import asyncio
import statistics
import threading
import time

import pytest
from fastapi.testclient import TestClient

from backend.api.routes_events import stream_events
from backend.api.schemas.tasks import ResearchStage
from backend.config import Settings
from backend.services.blocking_worker import run_blocking_worker
from backend.services.task_runner import TaskRunner


@pytest.mark.parametrize("operation", ["pdf", "vector", "model"])
def test_health_keepalive_and_cancellation_while_work_is_slow(tmp_path, app_factory, monkeypatch, operation):
    started = threading.Event()
    children = []
    original = asyncio.create_subprocess_exec
    async def slow_child(*args, **kwargs):
        child = await original(args[0], "-c", "import time; time.sleep(60)", **kwargs)
        children.append(child)
        started.set()
        return child
    monkeypatch.setattr(asyncio, "create_subprocess_exec", slow_child)
    class Graph:
        async def ainvoke(self, state, config):
            context = state["_run_context"]
            await context.stage_started(ResearchStage.READ)
            if operation == "model":
                started.set()
                await asyncio.sleep(60)
            else:
                await run_blocking_worker(operation, {}, 60)
    cfg = Settings(_env_file=None, database_path=str(tmp_path / "responsive.db"), event_keepalive_seconds=1)
    runner = TaskRunner(graph_factory=Graph, configuration=cfg)
    with TestClient(app_factory(cfg, runner=runner)) as client:
        manager = client.app.state.task_manager
        runner._event_recorder = client.app.state.event_recorder
        response = client.post("/api/v1/research/tasks", json={"client_request_id": operation, "query": "A slow research task"})
        assert response.status_code == 202
        assert started.wait(timeout=5)
        task_id = client.get("/api/v1/research/tasks/active").json()["id"]
        times = []
        for _ in range(10):
            now = time.monotonic()
            assert client.get("/health").status_code == 200
            times.append(time.monotonic() - now)
        p95 = sorted(times)[-1]
        assert p95 < 1
        async def heartbeat():
            recorder = client.app.state.event_recorder
            sequence = await recorder.repository.latest_sequence(task_id)
            response = await stream_events(task_id, after=sequence, last_event_id=None,
                                           manager=manager, recorder=recorder)
            before = time.monotonic()
            try:
                message = await asyncio.wait_for(anext(response.body_iterator), timeout=3)
                assert message.startswith(": keepalive")
                return time.monotonic() - before
            finally:
                await response.body_iterator.aclose()
        keepalive = client.portal.call(heartbeat)
        before = time.monotonic()
        assert client.post(f"/api/v1/research/tasks/{task_id}/cancel").status_code == 202
        client.portal.call(manager.wait_for_current_task)
        elapsed = time.monotonic() - before
        assert elapsed < 5
        snapshot = client.get(f"/api/v1/research/tasks/{task_id}").json()
        assert snapshot["status"] == "cancelled"
        assert all(child.returncode is not None for child in children)
        sequence = snapshot["last_sequence"]
        time.sleep(0.05)
        assert client.get(f"/api/v1/research/tasks/{task_id}").json()["last_sequence"] == sequence
        print(f"{operation}: health_max={p95:.3f}s keepalive={keepalive:.3f}s cancel={elapsed:.3f}s")
