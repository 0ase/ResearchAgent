import json

import pytest
from pydantic import ValidationError

from backend.api.schemas.events import EventType, ResearchEvent
from backend.api.schemas.results import ResearchTaskResult
from backend.api.schemas.tasks import (
    AcademicSource,
    CreateResearchTaskRequest,
    TaskStatus,
)
from backend.domain.tasks import effective_locale_for_task, transition_task


def test_task_status_is_a_closed_set() -> None:
    assert {status.value for status in TaskStatus} == {
        "queued",
        "running",
        "cancelling",
        "completed",
        "failed",
        "cancelled",
        "interrupted",
    }


def test_create_request_applies_task_limits_and_defaults() -> None:
    request = CreateResearchTaskRequest(
        client_request_id="request-1",
        query="How do transformers use attention?",
    )

    assert request.options.max_papers == 20
    assert request.options.sources == list(AcademicSource)
    assert request.options.output_language == "auto"


@pytest.mark.parametrize("max_papers", [0, 51])
def test_create_request_rejects_invalid_paper_limits(max_papers: int) -> None:
    with pytest.raises(ValidationError):
        CreateResearchTaskRequest(
            client_request_id="request-1",
            query="research",
            options={"max_papers": max_papers},
        )


def test_create_request_requires_at_least_one_source() -> None:
    with pytest.raises(ValidationError):
        CreateResearchTaskRequest(
            client_request_id="request-1",
            query="research",
            options={"sources": []},
        )


@pytest.mark.parametrize(
    ("query", "output_language", "expected"),
    [
        ("中文研究问题", "auto", "zh-CN"),
        ("English research question", "auto", "en"),
        ("中文研究问题", "en", "en"),
        ("English research question", "zh-CN", "zh-CN"),
    ],
)
def test_effective_locale_is_immutable_and_legacy_aware(
    query: str,
    output_language: str,
    expected: str,
) -> None:
    assert effective_locale_for_task(query, output_language) == expected


def test_event_requires_sequence_schema_version_and_type() -> None:
    event = ResearchEvent(
        task_id="task-1",
        sequence=1,
        schema_version=1,
        event_type=EventType.TASK_CREATED,
        payload={"query": "research"},
    )

    encoded = json.loads(event.model_dump_json())
    assert encoded["sequence"] == 1
    assert encoded["schema_version"] == 1
    assert encoded["event_type"] == "task.created"

    with pytest.raises(ValidationError):
        ResearchEvent(
            task_id="task-1",
            sequence=0,
            schema_version=0,
            event_type="unknown",
        )


def test_result_snapshot_serializes_with_explicit_empty_collections() -> None:
    result = ResearchTaskResult(
        task_id="task-1",
        report_markdown="# Report",
    )

    payload = result.model_dump()

    assert payload["papers"] == []
    assert payload["evidence"] == []
    assert payload["citations"] == []
    assert payload["capabilities"]["supports_replay"] is False


def test_illegal_task_transition_is_rejected() -> None:
    with pytest.raises(ValueError):
        transition_task(TaskStatus.COMPLETED, TaskStatus.RUNNING)
