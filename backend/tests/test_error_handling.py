"""Failure-path integration tests; no network or real research data required."""
import asyncio
import json
import logging
from logging.handlers import RotatingFileHandler
import sqlite3

import httpx
import pytest
from fastapi import BackgroundTasks, HTTPException
from fastapi.testclient import TestClient

from backend.api import routes_research
from backend.config import Settings, settings
from backend.core.observability import (
    ContextFilter, JsonFormatter, configure_logging, current_context,
    log_context, logger, trace_stage,
)
from backend.main import create_app
from backend.services import session_store


@pytest.fixture
def application(caplog, monkeypatch, tmp_path):
    monkeypatch.setattr(session_store, "DB_PATH", str(tmp_path / "research.db"))
    caplog.set_level(logging.INFO)
    context_filter = ContextFilter()
    caplog.handler.addFilter(context_filter)
    yield create_app()
    caplog.handler.removeFilter(context_filter)


def client_for(app):
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test",
    )


@pytest.mark.asyncio
async def test_unexpected_error_matches_log_and_hides_internal_details(application, caplog):
    @application.get("/fail")
    async def fail():
        try:
            raise ValueError("private-provider-detail")
        except ValueError as exc:
            raise RuntimeError("database-password") from exc

    async with client_for(application) as client:
        response = await client.get("/fail", headers={"X-Request-ID": "trace-123"})

    error = response.json()["error"]
    assert response.status_code == 500
    assert error["code"] == "INTERNAL_ERROR"
    assert error["request_id"] == response.headers["x-request-id"] == "trace-123"
    assert "private-provider-detail" not in response.text
    assert "database-password" not in response.text
    records = [r for r in caplog.records if getattr(r, "fields", {}).get("error_id") == error["error_id"]]
    assert len(records) == 1
    assert records[0].trace_context["request_id"] == "trace-123"
    formatted = json.loads(JsonFormatter().format(records[0]))
    assert "ValueError" in formatted["exception"] and "RuntimeError" in formatted["exception"]
    assert current_context() == {}


@pytest.mark.asyncio
async def test_validation_and_router_errors_share_contract(application):
    async with client_for(application) as client:
        invalid = await client.post("/api/research/stream", json={"query": " ", "private": "secret-input"})
        missing = await client.get("/missing")
        method = await client.post("/health")
        session = await client.get("/api/research/missing")
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "VALIDATION_ERROR"
    assert "input" not in invalid.json()["error"]["details"][0]
    assert "secret-input" not in invalid.text
    for response, code in ((missing, "NOT_FOUND"), (method, "METHOD_NOT_ALLOWED"), (session, "NOT_FOUND")):
        assert response.json()["error"]["code"] == code
        assert response.json()["error"]["request_id"] == response.headers["x-request-id"]
    assert method.headers["allow"] == "GET"


@pytest.mark.asyncio
async def test_http_exception_preserves_retry_headers(application):
    @application.get("/limited")
    async def limited():
        raise HTTPException(429, "Too many requests", headers={"Retry-After": "5"})

    async with client_for(application) as client:
        response = await client.get("/limited")
    assert response.status_code == 429 and response.headers["retry-after"] == "5"


@pytest.mark.asyncio
@pytest.mark.parametrize("exc,code,status", [
    (httpx.ReadTimeout("private timeout"), "UPSTREAM_TIMEOUT", 504),
    (httpx.ConnectError("private connection"), "UPSTREAM_UNAVAILABLE", 502),
    (sqlite3.OperationalError("private path"), "STORAGE_UNAVAILABLE", 503),
])
async def test_dependency_errors_are_classified(application, exc, code, status):
    @application.get("/dependency")
    async def dependency():
        raise exc

    async with client_for(application) as client:
        response = await client.get("/dependency")
    assert response.status_code == status
    assert response.json()["error"]["code"] == code
    assert "private" not in response.text


@pytest.mark.asyncio
async def test_concurrent_requests_and_stages_keep_context_isolated(application, caplog):
    @application.get("/parallel/{name}")
    async def parallel(name: str):
        async def operation(state):
            await asyncio.sleep(0.005)
            logger.info("parallel.operation")
            return current_context()
        return await trace_stage("parallel", operation)({})

    async with client_for(application) as client:
        responses = await asyncio.gather(*[
            client.get(f"/parallel/{i}", headers={"X-Request-ID": f"request-{i}"})
            for i in range(4)
        ])
        invalid_id = await client.get("/health", headers={"X-Request-ID": "invalid id"})
    for i, response in enumerate(responses):
        assert response.json()["request_id"] == f"request-{i}"
        assert response.json()["stage"] == "parallel"
    assert invalid_id.headers["x-request-id"] != "invalid id"
    assert len(invalid_id.headers["x-request-id"]) == 32
    assert current_context() == {}


def sse_events(response):
    return [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")]


@pytest.mark.asyncio
async def test_sse_failure_retains_context_and_traceback(application, monkeypatch, caplog):
    class FailingGraph:
        async def astream(self, *args, **kwargs):
            yield ((), {"step_count": 1, "next_agent": "writer"})
            async def writer(state):
                raise RuntimeError("private model failure")
            await trace_stage("writer", writer)({})

    monkeypatch.setattr(routes_research, "build_graph", FailingGraph)
    async with client_for(application) as client:
        response = await client.post("/api/research/stream", json={"query": "test"})
    events = sse_events(response)
    error = events[-1]
    assert response.status_code == 200
    assert error["event"] == "error" and error["code"] == "INTERNAL_ERROR"
    assert error["status_code"] == 500
    assert all(e["request_id"] == response.headers["x-request-id"] for e in events)
    assert "private model failure" not in response.text
    record = next(r for r in caplog.records if getattr(r, "fields", {}).get("error_id") == error["error_id"])
    assert record.trace_context["stage"] == "writer"
    assert record.trace_context["session_id"]
    assert record.exc_info
    assert current_context() == {}


@pytest.mark.asyncio
@pytest.mark.parametrize("endpoint", ["/api/research/", "/api/research/stream"])
async def test_save_failure_never_returns_success(application, monkeypatch, caplog, endpoint):
    class SuccessfulGraph:
        async def ainvoke(self, state):
            return {"raw_papers": [{"title": "paper"}], "final_answer": "report"}
        async def astream(self, *args, **kwargs):
            yield ((), await self.ainvoke({}))

    async def failing_save(**kwargs):
        raise sqlite3.OperationalError("disk full at private path")

    monkeypatch.setattr(routes_research, "build_graph", SuccessfulGraph)
    monkeypatch.setattr(routes_research, "save_session", failing_save)
    async with client_for(application) as client:
        response = await client.post(endpoint, json={"query": "test"})
    if endpoint.endswith("stream"):
        events = sse_events(response)
        assert all(e["event"] != "done" for e in events)
        error = events[-1]
    else:
        assert response.status_code == 503
        error = response.json()["error"]
    assert error["code"] == "SESSION_SAVE_FAILED"
    record = next(r for r in caplog.records if getattr(r, "fields", {}).get("error_id") == error["error_id"])
    assert record.trace_context["session_id"]
    assert "sqlite3.OperationalError" in JsonFormatter().format(record)


@pytest.mark.asyncio
async def test_success_persists_request_id(application, monkeypatch, tmp_path):
    class SuccessfulGraph:
        async def astream(self, *args, **kwargs):
            yield ((), {"raw_papers": [{"title": "paper"}], "final_answer": "report", "errors": ["partial evidence"]})
    monkeypatch.setattr(routes_research, "build_graph", SuccessfulGraph)
    monkeypatch.setattr(session_store, "DB_PATH", str(tmp_path / "research.db"))
    async with client_for(application) as client:
        response = await client.post("/api/research/stream", json={"query": "test"})
        done = sse_events(response)[-1]
        history = await client.get(f'/api/research/{done["session_id"]}')
    assert done["event"] == "done"
    assert history.json()["result"]["request_id"] == response.headers["x-request-id"]
    assert done["warnings"] == ["partial evidence"]


@pytest.mark.asyncio
async def test_cancelled_stream_closes_graph_and_pending_task(monkeypatch):
    monkeypatch.setattr(routes_research, "SSE_HEARTBEAT_SECONDS", 0.001)
    closed = asyncio.Event()
    async def source():
        try:
            await asyncio.sleep(60)
            yield "never"
        finally:
            closed.set()
    stream = routes_research._with_heartbeats(source())
    assert await anext(stream) is None
    await stream.aclose()
    assert closed.is_set()


def test_json_logs_redact_configured_secrets_urls_and_keep_tracebacks():
    formatter = JsonFormatter(["configured-secret"])
    try:
        raise RuntimeError("configured-secret Bearer hidden-token https://provider.test/api?api_key=hidden-key&email=private")
    except RuntimeError as exc:
        record = logging.LogRecord("backend", logging.ERROR, __file__, 1, str(exc), (), (type(exc), exc, exc.__traceback__))
        record.trace_context = {"request_id": "trace-1"}
        rendered = formatter.format(record)
    for secret in ("configured-secret", "hidden-token", "hidden-key", "email=private"):
        assert secret not in rendered
    assert json.loads(rendered)["request_id"] == "trace-1"
    assert "RuntimeError" in json.loads(rendered)["exception"]


def test_logging_configuration_is_idempotent_and_rotates(tmp_path):
    root = logging.getLogger()
    original_handlers, original_level = list(root.handlers), root.level
    config = Settings(_env_file=None, log_dir=str(tmp_path), log_max_bytes=1024, log_backup_count=2)
    try:
        configure_logging(config)
        configure_logging(config)
        owned = [h for h in root.handlers if getattr(h, "_bigone_handler", False)]
        assert len(owned) == 2
        file_handler = next(h for h in owned if isinstance(h, RotatingFileHandler))
        assert file_handler.backupCount == 2
        for _ in range(12):
            logger.info("rotation." + "x" * 150)
        assert (tmp_path / "backend.log.1").exists()
        assert len(list(tmp_path.glob("backend.log*"))) <= 3
    finally:
        for handler in list(root.handlers):
            if handler not in original_handlers:
                root.removeHandler(handler)
                handler.close()
        root.setLevel(original_level)


def test_application_lifecycle_configures_logging(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "log_dir", str(tmp_path))
    with TestClient(create_app()) as client:
        assert client.get("/health").status_code == 200
    logs = (tmp_path / "backend.log").read_text(encoding="utf-8")
    assert "application.started" in logs and "application.stopped" in logs


@pytest.mark.asyncio
@pytest.mark.parametrize("value", ["invalid", "[]"])
async def test_corrupt_stored_json_is_reported(application, monkeypatch, tmp_path, value):
    monkeypatch.setattr(session_store, "DB_PATH", str(tmp_path / "research.db"))
    await session_store.save_session("corrupt", "test", {"final_answer": "report"})
    db = await session_store._get_db()
    try:
        await db.execute("UPDATE sessions SET result_json = ? WHERE session_id = 'corrupt'", (value,))
        await db.commit()
    finally:
        await db.close()
    async with client_for(application) as client:
        response = await client.get("/api/research/corrupt")
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "STORED_DATA_INVALID"


@pytest.mark.asyncio
async def test_background_failure_is_logged_after_response_starts(application, caplog):
    def failing_task():
        raise RuntimeError("background failure")
    @application.get("/background")
    async def background(tasks: BackgroundTasks):
        tasks.add_task(failing_task)
        return {"ok": True}
    async with client_for(application) as client:
        response = await client.get("/background")
    assert response.status_code == 200
    assert any(r.exc_info and r.trace_context.get("request_id") == response.headers["x-request-id"] for r in caplog.records)


@pytest.mark.asyncio
async def test_sse_send_failure_closes_generator_context_and_graph(application, monkeypatch):
    from starlette.requests import ClientDisconnect
    from backend.api.schemas import ResearchRequest

    closed = asyncio.Event()
    class SlowGraph:
        async def astream(self, *args, **kwargs):
            try:
                yield ((), {"step_count": 1, "next_agent": "writer"})
                await asyncio.sleep(60)
            finally:
                closed.set()
    monkeypatch.setattr(routes_research, "build_graph", SlowGraph)
    response = await routes_research.start_research_stream(ResearchRequest(query="test"))
    async def send(message):
        if message["type"] == "http.response.body":
            raise OSError("client disconnected")
    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}
    with log_context(request_id="disconnect-test"):
        with pytest.raises(ClientDisconnect):
            await response({"type": "http", "asgi": {"spec_version": "2.4"}}, receive, send)
        assert current_context() == {"request_id": "disconnect-test"}
    assert closed.is_set()


@pytest.mark.asyncio
async def test_compiled_graph_traces_dynamic_supervisor_routing(application, monkeypatch, caplog):
    from langgraph.types import Command
    from backend.agents import graph

    async def supervisor(state):
        return Command(goto="writer", update={"step_count": 1})
    async def writer(state):
        raise httpx.ReadTimeout("model timed out")
    monkeypatch.setattr(graph, "supervisor", supervisor)
    monkeypatch.setattr(graph, "synthesize_review", writer)
    async with client_for(application) as client:
        response = await client.post("/api/research/", json={"query": "test"})
    assert response.status_code == 504
    error = response.json()["error"]
    record = next(r for r in caplog.records if getattr(r, "fields", {}).get("error_id") == error["error_id"])
    assert record.trace_context["stage"] == "writer"
    assert record.trace_context["session_id"]
