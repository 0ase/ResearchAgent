import asyncio
from datetime import datetime, timezone

import pytest
import pytest_asyncio

from backend.api.schemas.events import EventLevel, EventType
from backend.api.schemas.results import ResearchTaskResult
from backend.api.schemas.tasks import TaskSnapshot, TaskStatus
from backend.db.connection import open_database
from backend.repositories.event_repository import EventRepository
from backend.repositories.result_repository import ResultRepository
from backend.repositories.task_repository import TaskRepository
from backend.db.migrate import migrate_database
from backend.config import Settings


def make_task(
    task_id: str,
    client_request_id: str,
    *,
    status: TaskStatus = TaskStatus.QUEUED,
) -> TaskSnapshot:
    return TaskSnapshot(
        id=task_id,
        client_request_id=client_request_id,
        query="How do transformers use attention?",
        title="Transformer attention",
        status=status,
        created_at=datetime.now(timezone.utc),
    )


@pytest_asyncio.fixture
async def repositories(tmp_path):
    settings = Settings(_env_file=None, database_path=str(tmp_path / "research.db"))
    await migrate_database(settings)
    factory = lambda: open_database(settings)
    yield (
        TaskRepository(factory),
        EventRepository(factory),
        ResultRepository(factory),
    )


@pytest.mark.asyncio
async def test_create_and_read_task(repositories) -> None:
    tasks, _, _ = repositories
    task = make_task("task-1", "request-1")

    created = await tasks.create(task)
    loaded = await tasks.get("task-1")

    assert created.id == "task-1"
    assert loaded is not None
    assert loaded.query == task.query
    assert loaded.status is TaskStatus.QUEUED


@pytest.mark.asyncio
async def test_same_client_request_id_is_idempotent(repositories) -> None:
    tasks, _, _ = repositories

    first = await tasks.create(make_task("task-1", "request-1"))
    second = await tasks.create(make_task("task-2", "request-1"))

    assert second.id == first.id


@pytest.mark.asyncio
async def test_active_task_query_returns_only_one_active_task(repositories) -> None:
    tasks, _, _ = repositories

    await tasks.create(make_task("task-1", "request-1"))
    await tasks.create(make_task("task-2", "request-2", status=TaskStatus.COMPLETED))

    active = await tasks.get_active()

    assert active is not None
    assert active.id == "task-1"


@pytest.mark.asyncio
async def test_status_transition_uses_expected_old_status(repositories) -> None:
    tasks, _, _ = repositories
    await tasks.create(make_task("task-1", "request-1"))

    rejected = await tasks.transition_status(
        "task-1",
        expected_status=TaskStatus.RUNNING,
        target_status=TaskStatus.COMPLETED,
    )
    accepted = await tasks.transition_status(
        "task-1",
        expected_status=TaskStatus.QUEUED,
        target_status=TaskStatus.RUNNING,
    )

    assert rejected is None
    assert accepted is not None
    assert accepted.status is TaskStatus.RUNNING


@pytest.mark.asyncio
async def test_event_sequences_are_unique_and_ordered(repositories) -> None:
    tasks, events, _ = repositories
    await tasks.create(make_task("task-1", "request-1"))

    async def append(index: int):
        return await events.append(
            task_id="task-1",
            event_type=EventType.STAGE_PROGRESS,
            payload={"index": index},
        )

    appended = await asyncio.gather(*(append(index) for index in range(5)))
    sequences = sorted(event.sequence for event in appended)

    assert sequences == [1, 2, 3, 4, 5]
    assert [event.sequence for event in await events.list_events_after("task-1", 2)] == [3, 4, 5]


@pytest.mark.asyncio
async def test_result_upsert_and_read(repositories) -> None:
    tasks, _, results = repositories
    await tasks.create(make_task("task-1", "request-1"))
    result = ResearchTaskResult(task_id="task-1", report_markdown="# First")

    await results.upsert(result)
    loaded = await results.get("task-1")

    assert loaded is not None
    assert loaded.report_markdown == "# First"


@pytest.mark.asyncio
async def test_soft_deleted_task_is_hidden_from_history(repositories) -> None:
    tasks, _, _ = repositories
    await tasks.create(make_task("task-1", "request-1", status=TaskStatus.COMPLETED))

    assert await tasks.soft_delete("task-1") is True
    assert await tasks.get("task-1") is None
    assert await tasks.list_history() == []
