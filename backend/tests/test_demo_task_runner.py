import asyncio
from datetime import datetime, timezone

import pytest

from backend.api.schemas.events import EventType
from backend.api.schemas.tasks import TaskSnapshot, TaskStatus
from backend.services.demo_task_runner import DemoTaskRunner


class RecordingSink:
    def __init__(self) -> None:
        self.events = []

    async def append(self, **kwargs):
        self.events.append(kwargs)


def make_task() -> TaskSnapshot:
    return TaskSnapshot(
        id="demo-task",
        client_request_id="demo-request",
        query="How do retrieval systems improve scientific discovery?",
        title="Retrieval systems",
        status=TaskStatus.RUNNING,
        created_at=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_demo_runner_emits_complete_offline_workflow() -> None:
    sink = RecordingSink()
    runner = DemoTaskRunner(event_recorder=sink)

    state = await runner.run(make_task(), asyncio.Event())

    assert len(state["raw_papers"]) >= 5
    assert len(state["selected_papers"]) >= 4
    assert state["errors"] == []
    assert state["warnings"] == ["Crossref demo source unavailable"]
    statuses = {paper["full_text_status"] for paper in state["raw_papers"]}
    assert {"full", "abstract_only", "full_no_abstract", "unavailable"} <= statuses
    assert all(
        paper["full_text_status"] != "unavailable"
        for paper in state["selected_papers"]
    )
    assert state["final_answer"].startswith("# Retrieval systems")
    assert [event["stage"].value for event in sink.events if event["event_type"] is EventType.STAGE_STARTED] == [
        "orchestrate", "search", "filter", "read", "analyze", "synthesize", "critic",
    ]
    assert any(event["event_type"] is EventType.STAGE_WARNING for event in sink.events)
    assert [event["payload"]["attempt"] for event in sink.events if event["event_type"] is EventType.CRITIQUE_COMPLETED] == [1, 2]
    assert {event["event_type"] for event in sink.events} >= {
        EventType.PLAN_AVAILABLE,
        EventType.PAPERS_DISCOVERED,
        EventType.PAPERS_SELECTED,
        EventType.ANALYSIS_AVAILABLE,
        EventType.DRAFT_AVAILABLE,
    }


@pytest.mark.asyncio
async def test_demo_runner_honors_delay_and_cancellation() -> None:
    sink = RecordingSink()
    cancel_event = asyncio.Event()
    runner = DemoTaskRunner(event_recorder=sink, delay_seconds=0.02)
    task = asyncio.create_task(runner.run(make_task(), cancel_event))

    await asyncio.sleep(0.025)
    cancel_event.set()

    with pytest.raises(asyncio.CancelledError):
        await task
