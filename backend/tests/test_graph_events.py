import asyncio
from datetime import datetime, timezone

import pytest

from backend.api.schemas.events import EventType
from backend.api.schemas.tasks import TaskSnapshot, TaskStatus
from backend.domain.errors import ResearchPipelineError
from backend.services.event_recorder import EventRecorder
from backend.services.run_context import ResearchRunContext
from backend.services.task_runner import TaskRunner


class RecordingSink:
    def __init__(self) -> None:
        self.events = []

    async def append(self, **kwargs):
        self.events.append(kwargs)


class FakeGraph:
    async def astream(self, state, stream_mode):
        yield {"orchestrate": {"sub_queries": ["one", "two"]}}
        yield {
            "search": {
                "raw_papers": [{"title": "Paper"}],
                "search_diagnostics": [
                    {"source": "arxiv", "status": "ok", "papers": 2},
                    {
                        "source": "pubmed",
                        "status": "error",
                        "papers": 0,
                        "error_code": "SOURCE_TIMEOUT",
                    },
                ],
            }
        }
        yield {"critic": {"critique": {"score": 8}}}


class FailingGraph:
    async def astream(self, state, stream_mode):
        yield {"search": {"raw_papers": []}}
        raise RuntimeError("hidden provider response")


class DomainFailingGraph:
    async def astream(self, state, stream_mode):
        yield {"search": {"raw_papers": []}}
        raise ResearchPipelineError("NO_RESEARCH_RESULTS")


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
async def test_each_graph_node_emits_started_and_completed() -> None:
    sink = RecordingSink()
    runner = TaskRunner(graph_factory=lambda: FakeGraph(), event_recorder=sink)

    result = await runner.run(make_task(), asyncio.Event())

    assert result["critique"]["score"] == 8
    for stage in ["orchestrate", "search", "critic"]:
        stage_events = [event for event in sink.events if event.get("stage") == stage]
        assert [event["event_type"] for event in stage_events] == [
            EventType.STAGE_STARTED,
            EventType.STAGE_PROGRESS,
            EventType.STAGE_COMPLETED,
        ]

    search_progress = next(
        event
        for event in sink.events
        if event.get("stage") == "search" and event["event_type"] is EventType.STAGE_PROGRESS
    )
    assert search_progress["payload"]["source_stats"] == {
        "arxiv": {"papers": 2, "queries": 1, "errors": 0},
        "pubmed": {"papers": 0, "queries": 1, "errors": 1},
    }


@pytest.mark.asyncio
async def test_node_exception_emits_stage_failed_without_leaking_error() -> None:
    sink = RecordingSink()
    runner = TaskRunner(graph_factory=lambda: FailingGraph(), event_recorder=sink)

    with pytest.raises(RuntimeError):
        await runner.run(make_task(), asyncio.Event())

    failed = [event for event in sink.events if event["event_type"] is EventType.STAGE_FAILED]
    assert len(failed) == 1
    assert failed[0]["payload"] == {"code": "INTERNAL_ERROR"}
    assert "hidden provider response" not in str(failed[0])


@pytest.mark.asyncio
async def test_domain_exception_exposes_only_stable_stage_error_code() -> None:
    sink = RecordingSink()
    runner = TaskRunner(graph_factory=lambda: DomainFailingGraph(), event_recorder=sink)

    with pytest.raises(ResearchPipelineError):
        await runner.run(make_task(), asyncio.Event())

    failed = [event for event in sink.events if event["event_type"] is EventType.STAGE_FAILED]
    assert failed[-1]["payload"] == {"code": "NO_RESEARCH_RESULTS"}


@pytest.mark.asyncio
async def test_run_context_cancellation_is_checked_between_nodes() -> None:
    sink = RecordingSink()
    cancel_event = asyncio.Event()
    context = ResearchRunContext(task_id="task-1", event_recorder=sink, cancel_event=cancel_event)
    cancel_event.set()

    with pytest.raises(asyncio.CancelledError):
        context.raise_if_cancelled()
