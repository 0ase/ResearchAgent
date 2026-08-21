import asyncio
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from backend.api.dependencies import get_task_manager
from backend.api.schemas.tasks import TaskSnapshot, TaskStatus
from backend.config import Settings
from backend.db.connection import open_database
from backend.db.migrate import migrate_database
from backend.main import create_app
from backend.repositories.event_repository import EventRepository
from backend.repositories.result_repository import ResultRepository
from backend.repositories.task_repository import TaskRepository
from backend.services.task_manager import TaskManager


@pytest.fixture
def history_client(tmp_path):
    settings = Settings(_env_file=None, database_path=str(tmp_path / "research.db"))
    asyncio.run(migrate_database(settings))
    factory = lambda: open_database(settings)
    tasks = TaskRepository(factory)
    manager = TaskManager(tasks, EventRepository(factory), ResultRepository(factory))
    asyncio.run(
        tasks.create(
            TaskSnapshot(
                id="task-new",
                client_request_id="request-new",
                query="new",
                title="New",
                status=TaskStatus.COMPLETED,
                created_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
            )
        )
    )
    asyncio.run(
        tasks.create(
            TaskSnapshot(
                id="task-old",
                client_request_id="request-old",
                query="old",
                title="Old",
                status=TaskStatus.COMPLETED,
                created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            )
        )
    )
    asyncio.run(tasks.soft_delete("task-old"))
    app = create_app()
    app.dependency_overrides[get_task_manager] = lambda: manager
    with TestClient(app) as client:
        yield client


def test_history_is_newest_first_and_excludes_soft_deleted(history_client) -> None:
    response = history_client.get("/api/v1/research/history")

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == ["task-new"]
