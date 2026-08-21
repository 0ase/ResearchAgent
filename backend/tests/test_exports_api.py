import asyncio
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from backend.api.dependencies import get_task_manager
from backend.api.schemas.results import ResearchTaskResult
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
def export_client(tmp_path):
    settings = Settings(_env_file=None, database_path=str(tmp_path / "research.db"))
    asyncio.run(migrate_database(settings))
    factory = lambda: open_database(settings)
    tasks = TaskRepository(factory)
    results = ResultRepository(factory)
    manager = TaskManager(tasks, EventRepository(factory), results)
    asyncio.run(
        tasks.create(
            TaskSnapshot(
                id="task-1",
                client_request_id="request-1",
                query="research",
                title="Research",
                status=TaskStatus.COMPLETED,
                created_at=datetime.now(timezone.utc),
            )
        )
    )
    asyncio.run(
        results.upsert(
            ResearchTaskResult(
                task_id="task-1",
                report_markdown="# Report",
                papers=[
                    {
                        "title": "Attention Paper",
                        "authors": ["Ada Lovelace"],
                        "published_date": "2025",
                        "doi": "10.1000/example",
                        "source_id": "crossref:10.1000/example",
                    }
                ],
            )
        )
    )
    app = create_app()
    app.dependency_overrides[get_task_manager] = lambda: manager
    with TestClient(app) as client:
        yield client


def test_result_endpoint_returns_completed_result(export_client) -> None:
    response = export_client.get("/api/v1/research/tasks/task-1/result")

    assert response.status_code == 200
    assert response.json()["report_markdown"] == "# Report"


def test_export_formats_use_persisted_result(export_client) -> None:
    markdown = export_client.get(
        "/api/v1/research/tasks/task-1/export?format=markdown"
    )
    bibtex = export_client.get("/api/v1/research/tasks/task-1/export?format=bibtex")
    data = export_client.get("/api/v1/research/tasks/task-1/export?format=json")

    assert markdown.status_code == 200
    assert markdown.text == "# Report"
    assert "Attention Paper" in bibtex.text
    assert "10.1000/example" in bibtex.text
    assert data.json()["task_id"] == "task-1"
