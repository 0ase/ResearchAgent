import operator
from typing import Annotated, NotRequired, Optional
from typing_extensions import TypedDict

from backend.services.run_context import ResearchRunContext

class ResearchState(TypedDict):
    task_id: NotRequired[str]
    _run_context: NotRequired[ResearchRunContext]
    user_query: str
    max_papers: int
    sources: NotRequired[list[str]]
    output_language: NotRequired[str]
    research_plan: list[dict]
    raw_papers: Annotated[list[dict], operator.add]
    selected_papers: list[dict]
    analysis_report: Optional[dict]
    draft_sections: list[dict]
    figures: Annotated[list[dict], operator.add]
    merged_sections: list[dict]
    critique: Optional[dict]
    feedback: Optional[str]
    approved: bool
    search_round: int
    final_answer: Optional[str]
    errors: Annotated[list[str], operator.add]
    warnings: Annotated[list[str], operator.add]
    paper_insights: Annotated[list[dict], operator.add]
    paper_claims: Annotated[list[dict], operator.add]
    chunks: NotRequired[list[dict]]
    analysis_findings: Annotated[list[dict], operator.add]
    structured_report: NotRequired[Optional[dict]]
    draft_version: NotRequired[int]
    critique_round: int
    critique_history: Annotated[list[dict], operator.add]  # 累加每次评审记录
