"""Isolation is installed before test modules import the app or its settings."""
import os
from pathlib import Path
import tempfile

import pytest

_root = Path(tempfile.mkdtemp(prefix="research-tests-"))
os.environ["RESEARCH_TEST_ROOT"] = str(_root)
os.environ["RESEARCH_ENV_FILE"] = str(_root / ".env")
for _key in ("DEEPSEEK_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "DASHSCOPE_API_KEY",
             "CORS_ORIGINS", "DEFAULT_MODEL", "LIGHT_MODEL", "DEMO_INSTANCE_ID"):
    os.environ.pop(_key, None)
for _key, _value in {"DATABASE_PATH": "default.db", "PAPER_CACHE_DIR": "papers",
                     "CHROMA_PERSIST_DIR": "chroma", "FIGURES_DIR": "figures"}.items():
    os.environ[_key] = str(_root / _value)
os.environ["ENVIRONMENT"] = "test"
os.environ["RESEARCH_RUNNER_MODE"] = "real"


def pytest_configure(config):
    # All test paths must fall under one guard, even when pytest is invoked directly.
    config.option.basetemp = str(_root / "pytest")


@pytest.fixture(autouse=True)
def isolated_runtime(tmp_path, monkeypatch):
    from backend.config import current_settings
    cfg = current_settings()
    for name, value in {"database_path": str(tmp_path / "default.db"),
                        "paper_cache_dir": str(tmp_path / "papers"),
                        "chroma_persist_dir": str(tmp_path / "chroma"),
                        "figures_dir": str(tmp_path / "figures")}.items():
        monkeypatch.setattr(cfg, name, value)
        monkeypatch.setenv(name.upper(), value)
    # MockTransport and replaced model clients remain usable; real sockets do not.
    import socket
    original = socket.socket.connect
    def local_only(sock, address):
        if isinstance(address, tuple) and address[0] not in {"127.0.0.1", "localhost", "::1"}:
            raise AssertionError("External network access is disabled in backend tests")
        return original(sock, address)
    monkeypatch.setattr(socket.socket, "connect", local_only)
    original_ex = socket.socket.connect_ex
    def local_only_ex(sock, address):
        if isinstance(address, tuple) and address[0] not in {"127.0.0.1", "localhost", "::1"}:
            raise AssertionError("External network access is disabled in backend tests")
        return original_ex(sock, address)
    monkeypatch.setattr(socket.socket, "connect_ex", local_only_ex)
    import aiosqlite
    from backend.db.connection import validate_database_path
    original_connect = aiosqlite.connect
    def recorded_connect(database, *args, **kwargs):
        path = validate_database_path(database)
        with (_root / "connections.txt").open("a", encoding="utf-8") as record:
            record.write(str(path) + "\n")
        return original_connect(path, *args, **kwargs)
    monkeypatch.setattr(aiosqlite, "connect", recorded_connect)


def pytest_terminal_summary(terminalreporter):
    terminalreporter.write_line(f"Isolated database connections: {_root / 'connections.txt'}")


@pytest.fixture
def app_factory(tmp_path):
    from backend.config import current_settings
    from backend.main import create_app
    instances = 0
    def make(configuration=None, **kwargs):
        nonlocal instances
        instances += 1
        directory = tmp_path / f"application-{instances}"
        cfg = configuration or current_settings().model_copy(deep=True, update={
            "database_path": str(directory / "app.db"),
            "paper_cache_dir": str(directory / "papers"),
            "chroma_persist_dir": str(directory / "chroma"),
            "figures_dir": str(directory / "figures"),
        })
        return create_app(cfg, env_path=directory / ".env", **kwargs)
    return make
