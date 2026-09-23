"""Follow-up persistence and canonical compatibility transport regression tests."""
import asyncio
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from backend.api.errors import ApiError
from backend.api.schemas.tasks import TaskSnapshot, TaskStatus
from backend.api.schemas.results import ResearchTaskResult
from backend.api.schemas.events import EventType
from backend.config import settings
from backend.db.connection import open_database
from backend.db.migrate import migrate_database
from backend.repositories.task_repository import TaskRepository
from backend.repositories.result_repository import ResultRepository
from backend.repositories.event_repository import EventRepository
from backend.repositories.followup_repository import FollowUpRepository
from backend.services.followup_manager import FollowUpManager
from backend.main import create_app


async def setup(tmp_path, status=TaskStatus.RUNNING):
    path = tmp_path / "research.db"
    await migrate_database(path)
    factory = lambda: open_database(path)
    tasks, results, events = TaskRepository(factory), ResultRepository(factory), EventRepository(factory)
    await tasks.create(TaskSnapshot(id="t1",client_request_id="r1",query="Question",title="Question",
        status=status,created_at=datetime.now(timezone.utc)))
    return FollowUpRepository(factory), tasks, results, events

async def complete(tasks, results, events):
    await results.upsert(ResearchTaskResult(task_id="t1",report_markdown="An existing report"))
    await tasks.transition_status("t1",expected_status=TaskStatus.RUNNING,target_status=TaskStatus.COMPLETED)
    await events.append(task_id="t1",event_type=EventType.TASK_COMPLETED)

@pytest.mark.asyncio
async def test_queue_replace_cancel_and_request_id_idempotency(tmp_path):
    repo, tasks, results, events = await setup(tmp_path)
    await repo.put("t1","q1","Question one")
    await repo.put("t1","q1","Question one")
    assert await repo.claim() is None
    with pytest.raises(ApiError) as error:
        await repo.put("t1","q1","Different text")
    assert error.value.code == "MESSAGE_ID_CONFLICT"
    await repo.put("t1","q2","Question two")
    await repo.put("t1","q1","Question one")
    assert (await repo.snapshot("t1"))["pending"]["message_id"] == "q2"
    await repo.cancel("t1")
    assert (await repo.snapshot("t1"))["pending"] is None
    await repo.put("t1","q2","Question two")
    assert (await repo.snapshot("t1"))["pending"] is None

@pytest.mark.asyncio
async def test_waits_for_result_and_terminal_event_then_claims_once(tmp_path):
    repo, tasks, results, events = await setup(tmp_path)
    await repo.put("t1","q1","Question")
    assert await repo.claim() is None
    await complete(tasks, results, events)
    first, second = await asyncio.gather(repo.claim(),repo.claim())
    job = first or second
    assert bool(first) != bool(second)
    with pytest.raises(ApiError):
        await repo.put("t1","q2","Another")
    with pytest.raises(ApiError):
        await repo.cancel("t1")
    await repo.finish(job, {"answer":"An answer", "citations":[]})
    await repo.finish(job, {"answer":"Duplicate", "citations":[]})
    snapshot = await repo.snapshot("t1")
    assert [m["role"] for m in snapshot["messages"]] == ["user","assistant"]
    assert snapshot["messages"][-1]["content"] == "An answer"
    assert snapshot["pending"] is None

@pytest.mark.asyncio
@pytest.mark.parametrize("status",[TaskStatus.FAILED,TaskStatus.CANCELLED,TaskStatus.INTERRUPTED])
async def test_terminal_failure_deletes_question_content(tmp_path,status):
    repo, tasks, results, events = await setup(tmp_path)
    await repo.put("t1","q1","Sensitive queued question")
    await tasks.transition_status("t1",expected_status=TaskStatus.RUNNING,target_status=status)
    assert (await repo.snapshot("t1"))["pending"] is None
    db = await repo._connection_factory()
    try:
        assert await db.execute_fetchall("SELECT content FROM followup_jobs") == []
    finally:
        await db.close()

@pytest.mark.asyncio
async def test_restart_recovers_processing_and_failure_retains_retryable_question(tmp_path):
    repo, tasks, results, events = await setup(tmp_path)
    await complete(tasks, results, events)
    await repo.put("t1","q1","Question")
    await repo.claim()
    await repo.recover()
    job = await repo.claim()
    assert job["message_id"] == "q1"
    await repo.finish(job)
    assert (await repo.snapshot("t1"))["pending"]["status"] == "failed"
    await repo.put("t1","retry-q1","Question")
    assert (await repo.snapshot("t1"))["pending"]["status"] == "queued"


@pytest.mark.asyncio
async def test_restart_repairs_terminal_event_crash_window_once(tmp_path):
    repo, tasks, results, events = await setup(tmp_path)
    await repo.put("t1", "q1", "Question")
    await results.upsert(ResearchTaskResult(task_id="t1", report_markdown="Committed report"))
    await tasks.transition_status("t1", expected_status=TaskStatus.RUNNING, target_status=TaskStatus.COMPLETED)
    assert await repo.claim() is None
    await repo.recover()
    await repo.recover()
    assert (await repo.claim())["message_id"] == "q1"
    db = await repo._connection_factory()
    try:
        rows = await db.execute_fetchall("SELECT * FROM task_events WHERE event_type='task.completed'")
        assert len(rows) == 1
    finally:
        await db.close()

@pytest.mark.asyncio
async def test_worker_uses_context_only_and_does_not_mutate_report(tmp_path,monkeypatch):
    repo, tasks, results, events = await setup(tmp_path)
    await complete(tasks, results, events)
    monkeypatch.setattr(settings,"research_runner_mode","real")
    calls=[]
    async def answerer(question, session, history):
        calls.append(question)
        assert session["result"]["final_answer"] == "An existing report"
        assert history == []
        return {"answer":"Context answer [[CITE:invented]]","citations":["invented"]}
    manager=FollowUpManager(repo,tasks,results,answerer)
    await manager.start()
    try:
        await repo.put("t1","q1","Explain this")
        manager.wake()
        for _ in range(100):
            snapshot=await repo.snapshot("t1")
            if snapshot["messages"]:
                break
            await asyncio.sleep(0.01)
        assert calls == ["Explain this"]
        assert "invented" not in snapshot["messages"][-1]["content"]
        assert (await results.get("t1")).report_markdown == "An existing report"
    finally:
        await manager.shutdown()

def test_legacy_and_v1_use_the_same_completed_task(tmp_path,monkeypatch, app_factory):
    monkeypatch.setattr(settings,"database_path",str(tmp_path/"api.db"))
    monkeypatch.setattr(settings,"research_runner_mode","demo")
    monkeypatch.setattr(settings,"demo_delay_seconds",0)
    with TestClient(app_factory()) as client:
        response=client.post("/api/research/",json={"query":"A research question"})
        assert response.status_code == 200, response.text
        task_id=response.json()["session_id"]
        assert client.get(f"/api/v1/research/tasks/{task_id}").json()["status"] == "completed"
        payload={"message_id":"q1","message":"Explain the report"}
        first=client.post(f"/api/research/{task_id}/chat",json=payload)
        again=client.post(f"/api/research/{task_id}/chat",json=payload)
        assert first.status_code == 200, first.text
        assert first.json() == again.json()
        assert "[[CITE:" not in first.json()["answer"]
        legacy_messages = client.get(f"/api/research/{task_id}/messages").json()
        assert "[[CITE:" not in legacy_messages[-1]["content"]
        assert len(client.get(f"/api/v1/research/tasks/{task_id}/messages").json()["messages"]) == 2
        assert client.post("/api/research/",json={"query":"   "}).status_code == 422
        assert client.put(f"/api/v1/research/tasks/{task_id}/follow-up",json={"message_id":"blank","message":" "}).status_code == 422
