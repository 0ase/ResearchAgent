import asyncio
import hashlib

import pytest
from fastapi.testclient import TestClient

from backend.config import Settings
from backend.db.connection import open_database
from backend.db.migrate import migrate_database


def test_lifespan_does_not_touch_canary(tmp_path, app_factory):
    canary = tmp_path / "canary.db"
    asyncio.run(migrate_database(canary))
    before = hashlib.sha256(canary.read_bytes()).digest()
    cfg = Settings(_env_file=None, database_path=str(tmp_path / "app.db"), research_runner_mode="demo")
    with TestClient(app_factory(cfg)) as client:
        assert client.get("/health").json()["runner_mode"] == "demo"
        assert client.app.state.task_manager is not None
    assert hashlib.sha256(canary.read_bytes()).digest() == before


@pytest.mark.asyncio
async def test_default_user_database_is_rejected():
    with pytest.raises(RuntimeError, match="isolated test root"):
        await open_database("data/research.db")


def test_two_apps_have_separate_configuration(tmp_path, app_factory):
    a = Settings(_env_file=None, database_path=str(tmp_path / "a.db"), research_runner_mode="demo")
    b = Settings(_env_file=None, database_path=str(tmp_path / "b.db"), research_runner_mode="real")
    with TestClient(app_factory(a)) as first, TestClient(app_factory(b)) as second:
        assert first.get("/health").json()["runner_mode"] == "demo"
        assert second.get("/health").json()["runner_mode"] == "real"


def test_factory_allocates_fresh_paths_per_default_application(app_factory):
    first, second = app_factory(), app_factory()
    for name in ("database_path", "paper_cache_dir", "chroma_persist_dir", "figures_dir"):
        assert getattr(first.state.configuration, name) != getattr(second.state.configuration, name)
    assert first.state.env_path != second.state.env_path


def test_real_graph_and_followup_repositories_use_application_scope(tmp_path, app_factory, monkeypatch):
    from backend.config import settings
    from backend.api.schemas.tasks import CreateResearchTaskRequest
    from backend.repositories.paper_repository import PaperRepository
    from backend.repositories.chunk_repository import ChunkRepository
    from backend.services.task_runner import TaskRunner
    from backend.tests.evidence_fixture import evidence_state
    canary = tmp_path / "canary.db"
    asyncio.run(migrate_database(canary))
    before = hashlib.sha256(canary.read_bytes()).digest()
    monkeypatch.setattr(settings, "database_path", str(canary))
    cfg = Settings(_env_file=None, database_path=str(tmp_path / "scoped.db"), research_runner_mode="real")
    seen = []
    async def check_scope(label, task_id):
        assert settings.database_path == cfg.database_path
        assert settings.paper_cache_dir == cfg.paper_cache_dir
        assert settings.chroma_persist_dir == cfg.chroma_persist_dir
        db = await open_database()
        try:
            paths = await db.execute_fetchall("PRAGMA database_list")
            assert paths[0]["file"].replace("\\", "/") == str(tmp_path / "scoped.db").replace("\\", "/")
        finally:
            await db.close()
        await PaperRepository().list_for_task(task_id)
        await ChunkRepository().list_for_paper("paper-1")
        seen.append(label)
    class Graph:
        async def ainvoke(self, state, config):
            await check_scope("graph", state["task_id"])
            return evidence_state()
    monkeypatch.setattr(TaskRunner, "_make_graph", lambda self, context: Graph())
    async def answerer(question, state, messages):
        await check_scope("followup", state["result"]["task_id"])
        return {"answer": "An isolated answer", "citations": []}
    with TestClient(app_factory(cfg, answerer=answerer)) as client:
        manager = client.app.state.task_manager
        followup = client.app.state.followup_manager
        async def exercise():
            task = await manager.create_task(CreateResearchTaskRequest(client_request_id="scope", query="Configuration isolation"))
            await manager.wait_for_current_task()
            assert (await manager.tasks.get(task.id)).status.value == "completed"
            await followup.repository.put(task.id, "followup-1", "Scoped question")
            followup.wake()
            async with asyncio.timeout(3):
                while "followup" not in seen:
                    await asyncio.sleep(0.01)
        client.portal.call(exercise)
    assert seen == ["graph", "followup"]
    assert hashlib.sha256(canary.read_bytes()).digest() == before
