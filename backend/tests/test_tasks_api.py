import asyncio
import time

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


class SuccessfulRunner:
    async def run(self, task: TaskSnapshot, cancel_event: asyncio.Event) -> dict:
        await asyncio.sleep(0)
        return {
            "raw_papers": [{"paper_id": "paper-1", "title": "Paper 1"}],
            "paper_insights": [{"paper_id": "paper-1", "answer": "Summary"}],
            "final_answer": "# Report",
        }


class BlockingRunner:
    async def run(self, task: TaskSnapshot, cancel_event: asyncio.Event) -> None:
        while not cancel_event.is_set():
            await asyncio.sleep(0)


@pytest.fixture
def api_client(tmp_path):
    settings = Settings(_env_file=None, database_path=str(tmp_path / "research.db"))
    asyncio.run(migrate_database(settings))
    factory = lambda: open_database(settings)
    manager = TaskManager(
        TaskRepository(factory),
        EventRepository(factory),
        ResultRepository(factory),
        runner=SuccessfulRunner(),
    )
    app = create_app()
    app.dependency_overrides[get_task_manager] = lambda: manager
    with TestClient(app) as client:
        try:
            yield client, manager
        finally:
            client.portal.call(manager.shutdown)


def create_payload(client_request_id: str = "request-1") -> dict:
    return {
        "client_request_id": client_request_id,
        "query": "How do transformers use attention?",
    }


def wait_for_status(client: TestClient, task_id: str, status: str) -> dict:
    for _ in range(50):
        response = client.get(f"/api/v1/research/tasks/{task_id}")
        if response.json().get("status") == status:
            time.sleep(0.05)
            return response.json()
        time.sleep(0.01)
    raise AssertionError(f"task {task_id} did not reach {status}")


def test_create_task_returns_202_task_and_links(api_client) -> None:
    client, _ = api_client

    response = client.post("/api/v1/research/tasks", json=create_payload())

    assert response.status_code == 202
    body = response.json()
    assert body["task"]["id"]
    assert body["task"]["status"] == "queued"
    assert body["links"]["events"].endswith("/events")
    assert body["links"]["result"].endswith("/result")


def test_invalid_create_request_returns_validation_envelope(api_client) -> None:
    client, _ = api_client

    response = client.post(
        "/api/v1/research/tasks",
        json={**create_payload(), "query": "", "options": {"sources": []}},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_active_task_conflict_returns_409(api_client) -> None:
    client, manager = api_client
    manager.runner = BlockingRunner()

    first = client.post("/api/v1/research/tasks", json=create_payload())
    second = client.post(
        "/api/v1/research/tasks",
        json=create_payload("request-2"),
    )

    assert first.status_code == 202
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "ACTIVE_TASK_EXISTS"
    client.post(f"/api/v1/research/tasks/{first.json()['task']['id']}/cancel")
    wait_for_status(client, first.json()["task"]["id"], "cancelled")


def test_duplicate_client_request_is_idempotent(api_client) -> None:
    client, _ = api_client

    first = client.post("/api/v1/research/tasks", json=create_payload())
    second = client.post("/api/v1/research/tasks", json=create_payload())

    assert first.status_code == 202
    assert second.status_code == 202
    assert second.json()["task"]["id"] == first.json()["task"]["id"]


def test_active_endpoint_returns_200_or_204(api_client) -> None:
    client, manager = api_client
    manager.runner = BlockingRunner()

    assert client.get("/api/v1/research/tasks/active").status_code == 204
    created = client.post("/api/v1/research/tasks", json=create_payload())
    active = client.get("/api/v1/research/tasks/active")

    assert active.status_code == 200
    assert active.json()["id"] == created.json()["task"]["id"]
    client.post(f"/api/v1/research/tasks/{created.json()['task']['id']}/cancel")
    wait_for_status(client, created.json()["task"]["id"], "cancelled")
    assert client.get("/api/v1/research/tasks/active").status_code == 204


def test_get_snapshot_and_not_found(api_client) -> None:
    client, _ = api_client
    created = client.post("/api/v1/research/tasks", json=create_payload())
    task_id = created.json()["task"]["id"]

    assert client.get(f"/api/v1/research/tasks/{task_id}").status_code == 200
    missing = client.get("/api/v1/research/tasks/missing")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "TASK_NOT_FOUND"


def test_cancel_is_idempotent(api_client) -> None:
    client, manager = api_client
    manager.runner = BlockingRunner()
    created = client.post("/api/v1/research/tasks", json=create_payload())
    task_id = created.json()["task"]["id"]

    first = client.post(f"/api/v1/research/tasks/{task_id}/cancel")
    second = client.post(f"/api/v1/research/tasks/{task_id}/cancel")

    assert first.status_code == 202
    assert second.status_code == 202
    wait_for_status(client, task_id, "cancelled")


def test_retry_creates_new_task_with_parent_id(api_client) -> None:
    client, _ = api_client
    created = client.post("/api/v1/research/tasks", json=create_payload())
    original = wait_for_status(client, created.json()["task"]["id"], "completed")

    retried = client.post(f"/api/v1/research/tasks/{original['id']}/retry")

    assert retried.status_code == 202
    assert retried.json()["id"] != original["id"]
    assert retried.json()["parent_task_id"] == original["id"]


def test_patch_only_changes_display_title(api_client) -> None:
    client, _ = api_client
    created = client.post("/api/v1/research/tasks", json=create_payload())
    task_id = created.json()["task"]["id"]

    response = client.patch(
        f"/api/v1/research/tasks/{task_id}",
        json={"title": "Attention mechanisms — survey"},
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Attention mechanisms — survey"
    assert response.json()["query"] == create_payload()["query"]


def test_active_delete_is_rejected_and_terminal_delete_is_soft(api_client) -> None:
    client, manager = api_client
    manager.runner = BlockingRunner()
    created = client.post("/api/v1/research/tasks", json=create_payload())
    task_id = created.json()["task"]["id"]

    assert client.delete(f"/api/v1/research/tasks/{task_id}").status_code == 409
    client.post(f"/api/v1/research/tasks/{task_id}/cancel")
    wait_for_status(client, task_id, "cancelled")
    assert client.delete(f"/api/v1/research/tasks/{task_id}").status_code == 204
    assert client.get(f"/api/v1/research/tasks/{task_id}").status_code == 404
