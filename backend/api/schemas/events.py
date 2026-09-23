from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator

from backend.api.schemas.tasks import ResearchStage


class EventType(str, Enum):
    AGENT_DELEGATED = "agent.delegated"
    TASK_CREATED = "task.created"
    TASK_STARTED = "task.started"
    TASK_CANCELLATION_REQUESTED = "task.cancellation_requested"
    TASK_CANCELLED = "task.cancelled"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    TASK_INTERRUPTED = "task.interrupted"
    STAGE_STARTED = "stage.started"
    STAGE_PROGRESS = "stage.progress"
    STAGE_WARNING = "stage.warning"
    STAGE_COMPLETED = "stage.completed"
    STAGE_FAILED = "stage.failed"
    PLAN_AVAILABLE = "plan.available"
    PAPERS_DISCOVERED = "papers.discovered"
    PAPERS_SELECTED = "papers.selected"
    PAPER_READ = "paper.read"
    ANALYSIS_AVAILABLE = "analysis.available"
    DRAFT_AVAILABLE = "draft.available"
    CRITIQUE_COMPLETED = "critique.completed"
    EVIDENCE_AVAILABLE = "evidence.available"
    RESULT_AVAILABLE = "result.available"


class EventLevel(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class ReadProgressPayload(BaseModel):
    attempt: int = Field(ge=1)
    total: int = Field(ge=0)
    completed: int = Field(ge=0)
    succeeded: int = Field(ge=0)
    degraded: int = Field(ge=0)
    failed: int = Field(ge=0)
    metrics: dict[str, int] = Field(default_factory=dict)

    @model_validator(mode="after")
    def consistent_counts(self):
        if self.completed > self.total or self.completed != self.succeeded + self.degraded + self.failed:
            raise ValueError("Read progress counts are inconsistent")
        return self


class ResearchEvent(BaseModel):
    schema_version: int = Field(default=1, ge=1)
    task_id: str = Field(min_length=1)
    sequence: int = Field(ge=1)
    event_type: EventType
    stage: ResearchStage | None = None
    level: EventLevel = EventLevel.INFO
    payload: dict[str, Any] | ReadProgressPayload = Field(default_factory=dict)
    occurred_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )

    @model_validator(mode="after")
    def validate_read_progress(self):
        if isinstance(self.payload, ReadProgressPayload):
            self.payload = self.payload.model_dump()
        if self.event_type == EventType.STAGE_PROGRESS and self.stage == ResearchStage.READ and "total" in self.payload:
            ReadProgressPayload.model_validate(self.payload)
        return self
