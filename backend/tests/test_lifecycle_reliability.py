import asyncio
import subprocess
import sys

import pytest
from fastapi.testclient import TestClient

from backend.config import Settings
from backend.db.runtime_lock import DatabaseRuntimeLock, DatabaseInUseError
from backend.api.schemas.tasks import CreateResearchTaskRequest, TaskStatus
from backend.api.schemas.events import EventType


def test_second_owner_rejected_and_crash_releases_lock(tmp_path):
    path = tmp_path / "lock.db"
    code = "from backend.db.runtime_lock import DatabaseRuntimeLock; import sys,time; lock=DatabaseRuntimeLock(sys.argv[1]); lock.__enter__(); print('locked',flush=True); time.sleep(60)"
    child = subprocess.Popen([sys.executable, "-c", code, str(path)], stdout=subprocess.PIPE, text=True)
    try:
        assert child.stdout.readline().strip() == "locked"
        with pytest.raises(DatabaseInUseError):
            with DatabaseRuntimeLock(path):
                pass
    finally:
        child.kill()
        child.wait(timeout=5)
        child.stdout.close()
    with DatabaseRuntimeLock(path):
        pass


def test_second_app_cannot_recover_first_task(tmp_path, app_factory):
    cfg = Settings(_env_file=None, database_path=str(tmp_path / "shared.db"), research_runner_mode="demo", demo_delay_seconds=5)
    with TestClient(app_factory(cfg)) as first:
        response = first.post("/api/v1/research/tasks", json={"client_request_id":"owner", "query":"A scientific question"})
        assert response.status_code == 202
        with pytest.raises(DatabaseInUseError):
            with TestClient(app_factory(cfg)):
                pass
        assert first.get("/api/v1/research/tasks/active").status_code == 200


@pytest.mark.parametrize("failure_event", [EventType.TASK_CREATED, EventType.TASK_STARTED, EventType.TASK_COMPLETED])
def test_event_failure_rolls_back_lifecycle(tmp_path, app_factory, failure_event):
    cfg = Settings(_env_file=None, database_path=str(tmp_path / "tx.db"), research_runner_mode="demo")
    with TestClient(app_factory(cfg)) as client:
        manager = client.app.state.task_manager
        original = manager.events.append
        async def fail_once(**kwargs):
            if kwargs["event_type"] == failure_event:
                raise OSError("injected event failure")
            return await original(**kwargs)
        manager.events.append = fail_once
        request = CreateResearchTaskRequest(client_request_id="atomic", query="Atomic task research")
        if failure_event == EventType.TASK_CREATED:
            with pytest.raises(OSError):
                client.portal.call(manager.create_task, request)
            assert client.portal.call(manager.tasks.get_by_client_request_id, "atomic") is None
            assert client.get("/health").status_code == 503
            assert client.post("/api/v1/research/tasks", json={"client_request_id": "after-failure", "query": "Storage failure blocks new work"}).status_code == 503
        else:
            task = client.portal.call(manager.create_task, request)
            client.portal.call(manager.wait_for_current_task)
            loaded = client.portal.call(manager.tasks.get, task.id)
            assert loaded.status == TaskStatus.FAILED
            assert client.portal.call(manager.results.get, task.id) is None
            events = client.portal.call(manager.events.list_events_after, task.id)
            assert not any(e.event_type in {EventType.RESULT_AVAILABLE, EventType.TASK_COMPLETED} for e in events)


@pytest.mark.parametrize("cancel_first", [True, False])
def test_cancel_and_completion_have_one_terminal_result(app_factory, cancel_first):
    from backend.tests.evidence_fixture import evidence_state
    class Runner:
        async def run(self, task, cancel):
            await self.release.wait()
            return evidence_state()
    runner = Runner()
    with TestClient(app_factory(runner=runner)) as client:
        manager = client.app.state.task_manager
        async def compete():
            runner.release = asyncio.Event()
            task = await manager.create_task(CreateResearchTaskRequest(client_request_id="race", query="Lifecycle race"))
            await asyncio.sleep(0)
            if cancel_first:
                await manager.cancel_task(task.id)
            runner.release.set()
            await manager.wait_for_current_task()
            await manager.cancel_task(task.id)
            return task.id
        task_id = client.portal.call(compete)
        events = client.portal.call(manager.events.list_events_after, task_id)
        terminal = [e.event_type for e in events if e.event_type in {EventType.TASK_CANCELLED, EventType.TASK_COMPLETED, EventType.TASK_FAILED}]
        assert terminal == [EventType.TASK_CANCELLED if cancel_first else EventType.TASK_COMPLETED]
        assert (client.portal.call(manager.results.get, task_id) is None) == cancel_first


def test_restart_recovers_orphan_once(tmp_path, app_factory):
    from datetime import datetime, timezone
    from backend.api.schemas.tasks import TaskSnapshot
    from backend.db.migrate import migrate_database
    from backend.db.connection import open_database
    from backend.repositories.task_repository import TaskRepository
    cfg = Settings(_env_file=None, database_path=str(tmp_path / "orphan.db"))
    async def seed_crash():
        await migrate_database(cfg)
        await TaskRepository(lambda: open_database(cfg)).create(TaskSnapshot(
            id="orphan", client_request_id="orphan", query="Interrupted task", title="Orphan", status=TaskStatus.RUNNING,
            created_at=datetime.now(timezone.utc)))
    asyncio.run(seed_crash())
    for _ in range(2):
        with TestClient(app_factory(cfg)) as client:
            manager = client.app.state.task_manager
            assert client.get("/api/v1/research/tasks/orphan").json()["status"] == "interrupted"
            events = client.portal.call(manager.events.list_events_after, "orphan")
            assert [e.event_type for e in events] == [EventType.TASK_INTERRUPTED]


def test_invalid_read_counts_are_not_persisted(app_factory):
    from backend.api.schemas.tasks import ResearchStage
    from pydantic import ValidationError
    with TestClient(app_factory()) as client:
        manager = client.app.state.task_manager
        async def exercise():
            # No task row is needed: schema validation must precede its FK insert.
            with pytest.raises(ValidationError):
                await manager.events.append(task_id="invalid", event_type=EventType.STAGE_PROGRESS,
                    stage=ResearchStage.READ, payload={"attempt": 1, "total": 1, "completed": 1,
                                                      "succeeded": 1, "degraded": 1, "failed": 0})
            assert await manager.events.repository.latest_sequence("invalid") == 0
        client.portal.call(exercise)
