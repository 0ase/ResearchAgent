import asyncio
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from backend.api.dependencies import get_task_manager
from backend.api.routes_events import get_event_recorder
from backend.api.routes_events import stream_events
from backend.api.schemas.events import EventType
from backend.api.schemas.tasks import TaskSnapshot, TaskStatus
from backend.config import Settings
from backend.db.connection import open_database
from backend.db.migrate import migrate_database
from backend.main import create_app
from backend.repositories.event_repository import EventRepository
from backend.repositories.result_repository import ResultRepository
from backend.repositories.task_repository import TaskRepository
from backend.services.event_recorder import EventRecorder
from backend.services.task_manager import TaskManager


@pytest.fixture
def sse_client(tmp_path, monkeypatch):
    settings = Settings(_env_file=None, database_path=str(tmp_path / "research.db"))
    asyncio.run(migrate_database(settings))
    factory = lambda: open_database(settings)
    tasks = TaskRepository(factory)
    recorder = EventRecorder(EventRepository(factory))
    manager = TaskManager(tasks, recorder, ResultRepository(factory))
    app = create_app()
    app.dependency_overrides[get_task_manager] = lambda: manager
    app.dependency_overrides[get_event_recorder] = lambda: recorder
    monkeypatch.setattr("backend.main.settings.event_keepalive_seconds", 1)
    with TestClient(app) as client:
        yield client, tasks, recorder


def add_task(tasks: TaskRepository, task_id: str, status: TaskStatus) -> None:
    asyncio.run(
        tasks.create(
            TaskSnapshot(
                id=task_id,
                client_request_id=f"request-{task_id}",
                query="research",
                title="research",
                status=status,
                created_at=datetime.now(timezone.utc),
            )
        )
    )


def add_event(recorder: EventRecorder, task_id: str, event_type: EventType) -> None:
    asyncio.run(recorder.append(task_id=task_id, event_type=event_type))


def test_sse_includes_id_event_and_json_data(sse_client) -> None:
    client, tasks, recorder = sse_client
    add_task(tasks, "task-1", TaskStatus.COMPLETED)
    add_event(recorder, "task-1", EventType.STAGE_PROGRESS)

    with client.stream(
        "GET",
        "/api/v1/research/tasks/task-1/events?after=0",
        headers={"Accept": "text/event-stream"},
    ) as response:
        response_text = response.read().decode()

    assert response.status_code == 200
    assert "id: 1" in response_text
    assert "event: stage.progress" in response_text
    assert '"sequence": 1' in response_text


def test_sse_replays_only_events_after_cursor(sse_client) -> None:
    client, tasks, recorder = sse_client
    add_task(tasks, "task-1", TaskStatus.COMPLETED)
    add_event(recorder, "task-1", EventType.STAGE_STARTED)
    add_event(recorder, "task-1", EventType.STAGE_COMPLETED)

    with client.stream(
        "GET",
        "/api/v1/research/tasks/task-1/events?after=1",
        headers={"Accept": "text/event-stream"},
    ) as response:
        response_text = response.read().decode()

    assert "id: 1" not in response_text
    assert "id: 2" in response_text


def test_terminal_event_closes_sse_stream(sse_client) -> None:
    client, tasks, recorder = sse_client
    add_task(tasks, "task-1", TaskStatus.COMPLETED)
    add_event(recorder, "task-1", EventType.TASK_COMPLETED)

    with client.stream(
        "GET",
        "/api/v1/research/tasks/task-1/events",
        headers={"Accept": "text/event-stream"},
    ) as response:
        response_text = response.read().decode()

    assert response.status_code == 200
    assert "event: task.completed" in response_text


@pytest.mark.asyncio
async def test_idle_sse_emits_comment_keepalive(tmp_path, monkeypatch) -> None:
    settings = Settings(_env_file=None, database_path=str(tmp_path / "research.db"))
    await migrate_database(settings)
    factory = lambda: open_database(settings)
    tasks = TaskRepository(factory)
    recorder = EventRecorder(EventRepository(factory))
    manager = TaskManager(tasks, recorder, ResultRepository(factory))
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
    monkeypatch.setattr("backend.api.routes_events.settings.event_keepalive_seconds", 0.01)

    response = await stream_events(
        "task-1",
        after=0,
        last_event_id=None,
        manager=manager,
        recorder=recorder,
    )
    try:
        assert await response.body_iterator.__anext__() == ": keepalive\n\n"
    finally:
        await response.body_iterator.aclose()


def test_missing_task_returns_404(sse_client) -> None:
    client, _, _ = sse_client

    response = client.get("/api/v1/research/tasks/missing/events")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "TASK_NOT_FOUND"
