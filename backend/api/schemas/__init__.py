"""Public API schemas, including compatibility models for the legacy routes."""

from pydantic import BaseModel, Field

from backend.api.schemas.events import EventType, ResearchEvent
from backend.api.schemas.results import ResearchTaskResult
from backend.api.schemas.tasks import (
    AcademicSource,
    CreateResearchTaskRequest,
    ResearchStage,
    TaskSnapshot,
    TaskStatus,
)


class ResearchRequest(BaseModel):
    """Legacy request shape used by the existing Streamlit client."""

    query: str = Field(..., description="research question")
    max_papers: int = Field(default=10, ge=1, le=50)


class ResearchResponse(BaseModel):
    """Legacy response shape kept for `/api/research/`."""

    session_id: str
    research_plan: list[dict]
    papers_count: int
    final_answer: str


__all__ = [
    "AcademicSource",
    "CreateResearchTaskRequest",
    "EventType",
    "ResearchEvent",
    "ResearchRequest",
    "ResearchResponse",
    "ResearchStage",
    "ResearchTaskResult",
    "TaskSnapshot",
    "TaskStatus",
]
