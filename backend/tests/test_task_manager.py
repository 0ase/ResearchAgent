import asyncio
from datetime import datetime, timezone

import pytest
import pytest_asyncio

from backend.api.schemas.events import EventType
from backend.api.schemas.tasks import (
    CreateResearchTaskRequest,
    TaskSnapshot,
    TaskStatus,
)
from backend.config import Settings
from backend.db.connection import open_database
from backend.db.migrate import migrate_database
from backend.repositories.event_repository import EventRepository
from backend.repositories.result_repository import ResultRepository
from backend.repositories.task_repository import TaskRepository
from backend.services.task_manager import ActiveTaskError, TaskManager


class SuccessfulRunner:
    async def run(self, task: TaskSnapshot, cancel_event: asyncio.Event) -> dict:
        await asyncio.sleep(0)
        return {
            "raw_papers": [{"paper_id": "paper-1", "title": "Paper 1"}],
            "paper_insights": [{"paper_id": "paper-1", "answer": "Summary"}],
            "final_answer": "# Report",
        }


class EmptyResultRunner:
    async def run(self, task: TaskSnapshot, cancel_event: asyncio.Event) -> dict:
        await asyncio.sleep(0)
        return {}


class FailingRunner:
    async def run(self, task: TaskSnapshot, cancel_event: asyncio.Event) -> None:
        raise RuntimeError("secret model response")


class BlockingRunner:
    async def run(self, task: TaskSnapshot, cancel_event: asyncio.Event) -> None:
        while not cancel_event.is_set():
            await asyncio.sleep(0)


@pytest_asyncio.fixture
async def manager_context(tmp_path):
    settings = Settings(_env_file=None, database_path=str(tmp_path / "research.db"))
    await migrate_database(settings)
    factory = lambda: open_database(settings)
    repositories = (
        TaskRepository(factory),
        EventRepository(factory),
        ResultRepository(factory),
    )
    yield settings, repositories


def request(client_request_id: str = "request-1") -> CreateResearchTaskRequest:
    return CreateResearchTaskRequest(
        client_request_id=client_request_id,
        query="How do transformers use attention?",
    )


@pytest.mark.asyncio
async def test_create_starts_one_runner_and_completes(manager_context) -> None:
    _, (tasks, events, results) = manager_context
    manager = TaskManager(tasks, events, results, runner=SuccessfulRunner())

    task = await manager.create_task(request())
    await manager.wait_for_current_task()
    loaded = await tasks.get(task.id)

    assert loaded is not None
    assert loaded.status is TaskStatus.COMPLETED
    assert [event.event_type for event in await events.list_events_after(task.id)] == [
        EventType.TASK_CREATED,
        EventType.TASK_STARTED,
        EventType.RESULT_AVAILABLE,
        EventType.TASK_COMPLETED,
    ]


@pytest.mark.asyncio
async def test_active_task_rejects_second_request(manager_context) -> None:
    _, (tasks, events, results) = manager_context
    manager = TaskManager(tasks, events, results, runner=BlockingRunner())

    first = await manager.create_task(request())
    with pytest.raises(ActiveTaskError) as exc_info:
        await manager.create_task(request("request-2"))

    assert exc_info.value.task.id == first.id
    await manager.cancel_task(first.id)
    await manager.wait_for_current_task()


@pytest.mark.asyncio
async def test_duplicate_client_request_is_idempotent(manager_context) -> None:
    _, (tasks, events, results) = manager_context
    manager = TaskManager(tasks, events, results, runner=BlockingRunner())

    first = await manager.create_task(request())
    duplicate = await manager.create_task(request())

    assert duplicate.id == first.id
    await manager.cancel_task(first.id)
    await manager.wait_for_current_task()


@pytest.mark.asyncio
async def test_runner_exception_fails_with_safe_message(manager_context) -> None:
    _, (tasks, events, results) = manager_context
    manager = TaskManager(tasks, events, results, runner=FailingRunner())

    task = await manager.create_task(request())
    await manager.wait_for_current_task()
    loaded = await tasks.get(task.id)

    assert loaded is not None
    assert loaded.status is TaskStatus.FAILED
    assert loaded.error_code == "INTERNAL_ERROR"
    assert loaded.error_message == "研究任务执行失败"
    assert "secret" not in (loaded.error_message or "")


@pytest.mark.asyncio
async def test_empty_runner_result_fails_with_stable_domain_error(manager_context) -> None:
    _, (tasks, events, results) = manager_context
    manager = TaskManager(tasks, events, results, runner=EmptyResultRunner())

    task = await manager.create_task(request())
    await manager.wait_for_current_task()
    loaded = await tasks.get(task.id)
    task_events = await events.list_events_after(task.id)

    assert loaded is not None
    assert loaded.status is TaskStatus.FAILED
    assert loaded.error_code == "NO_RESEARCH_RESULTS"
    assert loaded.error_message == "未检索到可用论文"
    assert [event for event in task_events if event.event_type is EventType.RESULT_AVAILABLE] == []
    failed = [event for event in task_events if event.event_type is EventType.TASK_FAILED]
    assert failed[-1].payload == {"code": "NO_RESEARCH_RESULTS"}


@pytest.mark.asyncio
async def test_cancel_is_cooperative_and_ends_cancelled(manager_context) -> None:
    _, (tasks, events, results) = manager_context
    manager = TaskManager(tasks, events, results, runner=BlockingRunner())

    task = await manager.create_task(request())
    cancelling = await manager.cancel_task(task.id)
    await manager.wait_for_current_task()
    loaded = await tasks.get(task.id)

    assert cancelling.status is TaskStatus.CANCELLING
    assert loaded is not None
    assert loaded.status is TaskStatus.CANCELLED


@pytest.mark.asyncio
async def test_startup_marks_orphaned_active_tasks_interrupted(manager_context) -> None:
    _, (tasks, events, results) = manager_context
    for index, status in enumerate(
        [TaskStatus.QUEUED, TaskStatus.RUNNING, TaskStatus.CANCELLING],
        start=1,
    ):
        await tasks.create(
            TaskSnapshot(
                id=f"orphan-{index}",
                client_request_id=f"orphan-request-{index}",
                query="orphan",
                title="orphan",
                status=status,
                created_at=datetime.now(timezone.utc),
            )
        )

    manager = TaskManager(tasks, events, results, runner=SuccessfulRunner())
    await manager.recover_interrupted_tasks()

    for index in range(1, 4):
        loaded = await tasks.get(f"orphan-{index}")
        assert loaded is not None
        assert loaded.status is TaskStatus.INTERRUPTED


@pytest.mark.asyncio
async def test_shutdown_does_not_change_completed_task(manager_context) -> None:
    _, (tasks, events, results) = manager_context
    manager = TaskManager(tasks, events, results, runner=SuccessfulRunner())

    task = await manager.create_task(request())
    await manager.wait_for_current_task()
    await manager.shutdown()

    loaded = await tasks.get(task.id)
    assert loaded is not None
    assert loaded.status is TaskStatus.COMPLETED
