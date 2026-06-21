import operator
from typing import Annotated, Optional
from typing_extensions import TypedDict

class ResearchState(TypedDict):
    user_query: str
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
    paper_insights: Annotated[list[dict], operator.add]
    critique_round: int
    critique_history: Annotated[list[dict], operator.add]  # 累加每次评审记录
