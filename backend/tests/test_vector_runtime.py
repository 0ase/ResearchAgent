import asyncio
import json
import multiprocessing
import os
import threading
import time

import httpx
import pytest

from backend.api import routes_research
from backend.core.errors import AppError, VectorStoreUnavailable
from backend.main import create_app
from backend.rag import ingestion
from backend.rag.vector_runtime import VectorWorker


def crashing_worker(connection, persist_dir):
    connection.recv()
    os._exit(23)


def stalled_worker(connection, persist_dir):
    connection.recv()
    time.sleep(30)


def failing_operation_worker(connection, persist_dir):
    try:
        while connection.recv() is not None:
            connection.send({"ok": False, "traceback": "ValueError: incompatible vector dimension"})
    finally:
        connection.close()


def test_vectors_round_trip_and_persist_without_local_embedding_model(tmp_path):
    worker = VectorWorker(str(tmp_path / "chroma"), timeout=30)
    try:
        worker.call("paper", "add", ids=["one", "two"],
                    documents=["first evidence", "second evidence"],
                    embeddings=[[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]],
                    metadatas=[{"paper_id": "p1"}, {"paper_id": "p2"}])
        assert worker.call("paper", "count") == 2
        found = worker.call("paper", "get", where={"paper_id": "p1"})
        assert found["documents"] == ["first evidence"]
        nearest = worker.call("paper", "query", query_embeddings=[[1.0, 0.0, 0.0]], n_results=1)
        assert nearest["ids"][0] == ["one"]
    finally:
        worker.close()
    reopened = VectorWorker(str(tmp_path / "chroma"), timeout=30)
    try:
        assert reopened.call("paper", "count") == 2
        assert reopened.call("paper", "get", ids=["one"])["documents"] == ["first evidence"]
    finally:
        reopened.close()


@pytest.mark.asyncio
async def test_worker_crash_returns_sse_error_and_keeps_api_alive(monkeypatch, tmp_path, caplog):
    worker = VectorWorker(str(tmp_path), timeout=15, target=crashing_worker)
    class Graph:
        async def astream(self, *args, **kwargs):
            yield ((), {"step_count": 1, "next_agent": "read"})
            await asyncio.to_thread(worker.call, "paper", "get", ids=["one"])

    monkeypatch.setattr(routes_research, "build_graph", Graph)
    app = create_app()
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app, raise_app_exceptions=False),
            base_url="http://test",
        ) as client:
            response = await client.post("/api/research/stream", json={"query": "test"})
            health = await client.get("/health")
        events = [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")]
        error = events[-1]
        assert response.status_code == 200
        assert error["event"] == "error" and error["code"] == "VECTOR_STORE_UNAVAILABLE"
        assert error["status_code"] == 503
        assert error["request_id"] == response.headers["x-request-id"]
        assert error["error_id"]
        assert health.status_code == 200
        assert any("exit_code=23" in str(record.exc_info[1].__cause__)
                   for record in caplog.records if record.exc_info)
        # Fail fast after a fatal crash instead of spawning a crash loop.
        with pytest.raises(VectorStoreUnavailable):
            worker.call("paper", "get", ids=["two"])
    finally:
        worker.close()


def test_timeout_terminates_owned_worker(tmp_path):
    existing = {process.pid for process in multiprocessing.active_children()}
    worker = VectorWorker(str(tmp_path), timeout=0.1, target=stalled_worker)
    try:
        with pytest.raises(VectorStoreUnavailable):
            worker.call("paper", "get", ids=["one"])
        assert {process.pid for process in multiprocessing.active_children()} <= existing
    finally:
        worker.close()


def test_python_operation_error_retains_worker_traceback(tmp_path):
    worker = VectorWorker(str(tmp_path), timeout=15, target=failing_operation_worker)
    try:
        with pytest.raises(AppError) as captured:
            worker.call("paper", "query", query_embeddings=[[1.0]])
        assert captured.value.code == "VECTOR_OPERATION_FAILED"
        assert "incompatible vector dimension" in str(captured.value.__cause__)
    finally:
        worker.close()


@pytest.mark.asyncio
async def test_index_lookup_does_not_block_streaming_event_loop(monkeypatch):
    started, finished = threading.Event(), threading.Event()
    async def ticker():
        while not started.is_set():
            await asyncio.sleep(0.001)
        await asyncio.sleep(0.005)
        assert not finished.is_set()
    def slow_lookup(paper_id):
        started.set()
        time.sleep(0.1)
        finished.set()
        return True
    monkeypatch.setattr(ingestion, "is_paper_indexed", slow_lookup)
    result, _ = await asyncio.gather(ingestion.ingest_paper({"source_id": "p1"}), ticker())
    assert result is True
