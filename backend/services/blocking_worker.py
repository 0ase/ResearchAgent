"""Short-lived PDF/Chroma worker. Never opens the research database."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
import ctypes
from contextlib import redirect_stdout
import json
import os
import sys
import threading
import time

_file_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="research-file")


async def file_io(function, *args):
    future = asyncio.get_running_loop().run_in_executor(_file_executor, function, *args)
    try:
        return await asyncio.shield(future)
    except asyncio.CancelledError:
        # A file must not be closed/unlinked while its submitted write still runs.
        await future
        raise


async def run_blocking_worker(operation, payload, timeout):
    executable, environment = sys.executable, None
    # Match CPython multiprocessing's Windows venv handling (bpo-35797).
    # Killing the venv redirector alone would leave the real interpreter alive.
    if os.name == "nt" and os.path.normcase(sys.executable) != os.path.normcase(sys._base_executable):
        executable = sys._base_executable
        environment = {**os.environ, "__PYVENV_LAUNCHER__": sys.executable}
    process = await asyncio.create_subprocess_exec(
        executable, "-m", "backend.services.blocking_worker", str(os.getpid()),
        stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
        env=environment,
    )
    try:
        async with asyncio.timeout(timeout):
            stdout, _ = await process.communicate(json.dumps({"operation": operation, **payload}).encode())
            if process.returncode != 0:
                raise RuntimeError("BLOCKING_WORKER_FAILED")
            response = json.loads(stdout)
            if not response.get("ok"):
                raise RuntimeError("BLOCKING_WORKER_FAILED")
            return response.get("result")
    finally:
        if process.returncode is None:
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), timeout=1)
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()


def _watch_parent(parent_pid):
    if os.name == "nt":
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.restype = ctypes.c_void_p
        kernel.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
        handle = kernel.OpenProcess(0x00100000, False, parent_pid)
        if not handle:
            os._exit(1)
        kernel.WaitForSingleObject(handle, 0xFFFFFFFF)
    else:
        while os.getppid() == parent_pid:
            time.sleep(0.2)
    os._exit(1)


def _execute(payload):
    if payload["operation"] == "pdf":
        from backend.services.chunking import chunk_paper
        return chunk_paper(payload["path"], paper_id=payload["paper_id"],
                           chunk_size=payload["chunk_size"], overlap=payload["chunk_overlap"])
    if payload["operation"] == "vector":
        from backend.config import Settings, settings_scope
        from backend.rag.vector_store import add_chunks
        with settings_scope(Settings(_env_file=None, chroma_persist_dir=payload["directory"])):
            add_chunks(payload["chunks"], payload["embeddings"], payload["paper_id"])
        return True
    raise ValueError("Unknown operation")


if __name__ == "__main__":
    threading.Thread(target=_watch_parent, args=(int(sys.argv[1]),), daemon=True).start()
    try:
        with redirect_stdout(sys.stderr):
            value = _execute(json.load(sys.stdin))
        print(json.dumps({"ok": True, "result": value}))
    except Exception:
        print(json.dumps({"ok": False}))
