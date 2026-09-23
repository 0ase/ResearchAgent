import asyncio
from datetime import datetime, timezone

import pytest
import pytest_asyncio

from backend.api.schemas.events import EventType
from backend.api.schemas.tasks import TaskSnapshot, TaskStatus
from backend.config import Settings
from backend.db.connection import open_database
from backend.db.migrate import migrate_database
from backend.repositories.event_repository import EventRepository
from backend.repositories.result_repository import ResultRepository
from backend.repositories.task_repository import TaskRepository
from backend.services.event_recorder import EventRecorder


@pytest_asyncio.fixture
async def recorder_context(tmp_path):
    settings = Settings(_env_file=None, database_path=str(tmp_path / "research.db"))
    await migrate_database(settings)
    factory = lambda: open_database(settings)
    tasks = TaskRepository(factory)
    recorder = EventRecorder(EventRepository(factory))
    await tasks.create(
        TaskSnapshot(
            id="task-1",
            client_request_id="request-1",
            query="research",
            title="research",
            status=TaskStatus.RUNNING,
            created_at=datetime.now(timezone.utc),
        )
    )
    yield tasks, recorder, ResultRepository(factory)


@pytest.mark.asyncio
async def test_event_recorder_persists_and_increments_sequence(recorder_context) -> None:
    _, recorder, _ = recorder_context

    first = await recorder.append(
        task_id="task-1",
        event_type=EventType.STAGE_STARTED,
        payload={"stage": "search"},
    )
    second = await recorder.append(
        task_id="task-1",
        event_type=EventType.STAGE_COMPLETED,
    )

    assert first.sequence == 1
    assert second.sequence == 2
    assert [
        event.sequence for event in await recorder.list_events_after("task-1", 0)
    ] == [1, 2]


@pytest.mark.asyncio
async def test_waiter_is_notified_after_durable_write(recorder_context) -> None:
    _, recorder, _ = recorder_context
    await recorder.append(task_id="task-1", event_type=EventType.STAGE_STARTED)

    waiter = asyncio.create_task(
        recorder.wait_for_event("task-1", after_sequence=1, timeout=1)
    )
    await asyncio.sleep(0)
    await recorder.append(task_id="task-1", event_type=EventType.STAGE_COMPLETED)

    assert await waiter is True


@pytest.mark.asyncio
async def test_waiter_times_out_without_writing_a_keepalive_event(recorder_context) -> None:
    _, recorder, _ = recorder_context

    assert await recorder.wait_for_event("task-1", after_sequence=0, timeout=0.01) is False
    assert await recorder.list_events_after("task-1", 0) == []
