from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class TaskStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    CANCELLING = "cancelling"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    INTERRUPTED = "interrupted"


class ResearchStage(str, Enum):
    ORCHESTRATE = "orchestrate"
    SEARCH = "search"
    FILTER = "filter"
    READ = "read"
    ANALYZE = "analyze"
    SYNTHESIZE = "synthesize"
    CRITIC = "critic"


class StageStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    WARNING = "warning"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AcademicSource(str, Enum):
    ARXIV = "arxiv"
    SEMANTIC_SCHOLAR = "semantic_scholar"
    PUBMED = "pubmed"
    CROSSREF = "crossref"


Locale = Literal["zh-CN", "en"]
OutputLanguage = Literal["auto", "zh-CN", "en"]


class ResearchTaskOptions(BaseModel):
    max_papers: int = Field(default=20, ge=1, le=50)
    sources: list[AcademicSource] = Field(
        default_factory=lambda: list(AcademicSource),
        min_length=1,
    )
    output_language: OutputLanguage = "auto"

    @field_validator("sources")
    @classmethod
    def reject_duplicate_sources(
        cls,
        value: list[AcademicSource],
    ) -> list[AcademicSource]:
        if len(set(value)) != len(value):
            raise ValueError("sources must not contain duplicates")
        return value


class CreateResearchTaskRequest(BaseModel):
    client_request_id: str = Field(min_length=1, max_length=200)
    query: str = Field(min_length=1, max_length=2000)
    options: ResearchTaskOptions = Field(default_factory=ResearchTaskOptions)

    @field_validator("query")
    @classmethod
    def normalize_query(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("query must not be blank")
        return normalized


class TaskProgress(BaseModel):
    message: str | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)


class StageSnapshot(BaseModel):
    stage: ResearchStage
    status: StageStatus = StageStatus.PENDING
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_ms: int | None = Field(default=None, ge=0)
    detail: str | None = None
    attempt: int = Field(default=1, ge=1)


class TaskSnapshot(BaseModel):
    id: str
    parent_task_id: str | None = None
    client_request_id: str
    query: str
    title: str
    status: TaskStatus
    effective_locale: Locale = "en"
    current_stage: ResearchStage | None = None
    options: dict[str, Any] = Field(default_factory=dict)
    progress: TaskProgress = Field(default_factory=TaskProgress)
    stages: list[StageSnapshot] = Field(default_factory=list)
    statistics: dict[str, Any] = Field(default_factory=dict)
    last_sequence: int = Field(default=0, ge=0)
    available_actions: list[str] = Field(default_factory=list)
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_code: str | None = None
    error_message: str | None = None


class TaskLinks(BaseModel):
    self: str
    events: str
    result: str


class CreateTaskResponse(BaseModel):
    task: TaskSnapshot
    links: TaskLinks


class UpdateTaskRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("title must not be blank")
        return normalized
