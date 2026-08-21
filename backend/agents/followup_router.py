from typing import Literal

from pydantic import BaseModel
from typing_extensions import TypedDict


class FollowUpDecision(BaseModel):
    mode: Literal[
        "answer_from_context",
        "retrieve_more",
        "revise_report",
        "new_research",
    ]
    reason: str
    retrieval_query: str | None = None

class FollowUpState(TypedDict, total=False):
    session_id: str
    original_query: str
    followup_question: str
    mode: str

    report: str
    existing_insights: list[dict]
    new_insights: list[dict]
    messages: list[dict]
    answer: str
    errors: list[str]
