import asyncio
from datetime import datetime, timezone

import pytest

from backend.api.schemas.events import EventType
from backend.api.schemas.tasks import TaskSnapshot, TaskStatus
from backend.services.run_context import ResearchRunContext
from backend.services.task_runner import TaskRunner


class CancellingSink:
    def __init__(self, cancel_event: asyncio.Event) -> None:
        self.cancel_event = cancel_event
        self.events = []

    async def append(self, **kwargs):
        self.events.append(kwargs)
        if kwargs.get("event_type") is EventType.STAGE_COMPLETED:
            self.cancel_event.set()


class TwoStageGraph:
    async def astream(self, state, stream_mode):
        yield {"search": {"raw_papers": [{"title": "Paper"}]}}
        yield {"read": {"paper_insights": [{"answer": "summary"}]}}


def make_task() -> TaskSnapshot:
    return TaskSnapshot(
        id="task-1",
        client_request_id="request-1",
        query="research",
        title="research",
        status=TaskStatus.RUNNING,
        created_at=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_cancellation_stops_before_next_graph_node() -> None:
    cancel_event = asyncio.Event()
    sink = CancellingSink(cancel_event)
    runner = TaskRunner(graph_factory=lambda: TwoStageGraph(), event_recorder=sink)

    with pytest.raises(asyncio.CancelledError):
        await runner.run(make_task(), cancel_event)

    event_types = [event["event_type"] for event in sink.events]
    assert event_types == [
        EventType.STAGE_STARTED,
        EventType.STAGE_PROGRESS,
        EventType.STAGE_COMPLETED,
    ]
