from typing import Any
from typing_extensions import TypedDict

class StoredResearchResult(TypedDict, total=False):
    final_answer: str
    critique: dict[str, Any] | None
    papers: list[dict[str, Any]]
    paper_insights: list[dict[str, Any]]
    analysis: dict[str, Any]
    agent_trace: list[dict[str, Any]]
    finish_reason: str
    writer_finish_reason: str
    writer_generation_attempts: int
    writer_incomplete: bool

class StoredSession(TypedDict, total=False):
    session_id: str
    query: str
    created_at: str
    papers_count: int
    score: str
    result: StoredResearchResult
