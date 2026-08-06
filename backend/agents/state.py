import operator
from typing import Annotated, Optional
from typing_extensions import TypedDict


class ResearchState(TypedDict, total=False):
    user_query: str

    research_plan: list[dict]
    raw_papers: list[dict]
    selected_papers: list[dict]
    paper_insights: list[dict]
    analysis_report: Optional[dict]
    draft_sections: list[dict]
    critique: Optional[dict]
    feedback: Optional[str]
    approved: bool
    final_answer: Optional[str]

    search_round: int
    critique_round: int
    critique_history: Annotated[list[dict], operator.add]
    errors: Annotated[list[str], operator.add]

    current_task: str
    next_agent: str
    decision_reason: str
    step_count: int
    max_steps: int
    status: str
    finish_reason: str
    max_papers: int

    previous_queries: list[str]
    search_review: dict
    search_gaps: list[str]
    search_feedback: str
    retrieval_exhausted: bool
