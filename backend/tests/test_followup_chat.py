from collections import Counter
import asyncio

import httpx
import pytest

from backend.api import routes_research
from backend.main import app
from backend.services import session_store


def _research_result() -> dict:
    return {
        "final_answer": "这是一份测试研究报告。",
        "analysis": {"themes": ["主题一"]},
        "paper_insights": [{"source": "paper-1", "answer": "测试证据"}],
        "papers": [],
        "critique": {"score": 8},
    }


@pytest.mark.asyncio
async def test_message_store_round_trip_is_ordered(tmp_path, monkeypatch):
    monkeypatch.setattr(session_store, "DB_PATH", str(tmp_path / "research.db"))

    await session_store.save_session("session-1", "原始问题", _research_result())
    await session_store.add_message(
        "session-1", "question-1", "user", "第一个追问", []
    )
    await session_store.add_message(
        "session-1", "answer-1", "assistant", "第一个回答", ["paper-1"]
    )

    messages = await session_store.get_messages("session-1")

    assert [message["role"] for message in messages] == [
        "user",
        "assistant",
        "user",
        "assistant",
    ]
    assert messages[-1]["citations"] == ["paper-1"]
    assert await session_store.get_messages("missing-session") == []


@pytest.mark.asyncio
async def test_followup_endpoint_and_retry_are_idempotent(tmp_path, monkeypatch):
    monkeypatch.setattr(session_store, "DB_PATH", str(tmp_path / "research.db"))
    await session_store.save_session("session-1", "原始问题", _research_result())

    calls = Counter()

    async def fake_answer_followup(question, session, messages):
        calls["agent"] += 1
        assert question == "请解释主题一"
        assert all(message["content"] != question for message in messages)
        return {
            "answer": "主题一的解释。[Source paper-1]",
            "citations": ["paper-1"],
            "mode": "answer_from_context",
        }

    monkeypatch.setattr(routes_research, "answer_followup", fake_answer_followup)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {"message": "请解释主题一", "message_id": "question-1"}
        first = await client.post("/api/research/session-1/chat", json=payload)
        retry = await client.post("/api/research/session-1/chat", json=payload)
        history = await client.get("/api/research/session-1/messages")

    assert first.status_code == 200
    assert retry.status_code == 200
    assert first.json() == retry.json()
    assert first.json()["citations"] == ["paper-1"]
    assert calls["agent"] == 1
    assert [message["role"] for message in history.json()] == [
        "user",
        "assistant",
        "user",
        "assistant",
    ]


@pytest.mark.asyncio
async def test_followup_rejects_blank_message(tmp_path, monkeypatch):
    monkeypatch.setattr(session_store, "DB_PATH", str(tmp_path / "research.db"))
    await session_store.save_session("session-1", "原始问题", _research_result())

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/research/session-1/chat",
            json={"message": "   ", "message_id": "question-1"},
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_research_rejects_blank_query_before_starting_graph():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/research/stream",
            json={"query": "   ", "max_papers": 8},
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_sse_heartbeat_does_not_cancel_slow_graph(monkeypatch):
    monkeypatch.setattr(routes_research, "SSE_HEARTBEAT_SECONDS", 0.005)

    async def slow_graph():
        await asyncio.sleep(0.02)
        yield ((), {"status": "completed"})

    events = []
    async for item in routes_research._with_heartbeats(slow_graph()):
        events.append(item)

    assert None in events
    assert events[-1] == ((), {"status": "completed"})
