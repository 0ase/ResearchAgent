"""Actual PowerShell supervisor + actual backend; only the frontend is a stub."""
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import time

import httpx
import pytest


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.mark.skipif(os.name != "nt", reason="Windows launcher")
@pytest.mark.parametrize("failure", ["backend", "frontend"])
def test_launcher_observes_exit_and_preserves_logs(tmp_path, failure):
    api_port, web_port = free_port(), free_port()
    frontend = tmp_path / "frontend.py"
    frontend.write_text('''import os
from http.server import BaseHTTPRequestHandler, HTTPServer
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/exit': os._exit(0)
        self.send_response(200); self.end_headers(); self.wfile.write(b'{}')
HTTPServer(('127.0.0.1', int(os.environ['RESEARCH_WEB_PORT'])), Handler).serve_forever()
''', encoding="utf-8")
    (tmp_path / "npm.cmd").write_text(f'@echo off\n"{sys.executable}" "{frontend}"\n', encoding="utf-8")
    output = tmp_path / "launcher.log"
    env = {**os.environ, "PATH": str(tmp_path) + os.pathsep + os.environ["PATH"],
           "PYTHON_EXE": sys.executable, "RESEARCH_API_PORT": str(api_port), "RESEARCH_WEB_PORT": str(web_port),
           "DATABASE_PATH": str(tmp_path / "launcher.db"), "RESEARCH_ENV_FILE": str(tmp_path / ".env")}
    with output.open("w", encoding="utf-8") as log:
        process = subprocess.Popen(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                                    "scripts/start_agent.ps1", "-NoBrowser"], env=env, stdout=log, stderr=log)
        backend_pid = None
        try:
            deadline = time.monotonic() + 35
            while time.monotonic() < deadline:
                text = output.read_text(encoding="utf-8", errors="replace")
                match = re.search(r"Real backend is ready.*PID (\d+)", text)
                if match: backend_pid = int(match[1])
                if "Research Agent is running" in text: break
                if process.poll() is not None: pytest.fail(text)
                time.sleep(0.1)
            else:
                pytest.fail(output.read_text(encoding="utf-8", errors="replace"))
            assert backend_pid is not None
            match = re.search(r"Runtime logs: (.+)", text)
            log_root = Path(match[1].strip())
            before = time.monotonic()
            if failure == "backend":
                # An unsolicited backend exit (even code 0) must fail supervision.
                (log_root / "backend.stop").touch()
            else:
                try:
                    httpx.get(f"http://127.0.0.1:{web_port}/exit", timeout=2)
                except httpx.TransportError:
                    pass
            code = process.wait(timeout=20)
            elapsed = time.monotonic() - before
            text = output.read_text(encoding="utf-8", errors="replace")
            assert (code != 0) if failure == "backend" else (code == 0)
            assert "Logs:" in text
            match = re.search(r"Runtime logs: (.+)", text)
            log_root = Path(match[1].strip())
            assert (log_root / "backend.stderr.log").exists()
            assert (log_root / "frontend.stdout.log").exists()
            for port in (api_port, web_port):
                with socket.socket() as probe:
                    assert probe.connect_ex(("127.0.0.1", port)) != 0, "Owned child still listening after launcher exit"
            if failure == "frontend":
                assert "Application shutdown complete" in (log_root / "backend.stderr.log").read_text(errors="replace")
            print(f"launcher {failure} exit: {elapsed:.3f}s, code={code}")
        finally:
            try:
                httpx.get(f"http://127.0.0.1:{web_port}/exit", timeout=1)
            except httpx.TransportError:
                pass
            if process.poll() is None:
                # Killing the owning launcher triggers the backend parent watcher.
                process.kill()
                process.wait(timeout=5)
