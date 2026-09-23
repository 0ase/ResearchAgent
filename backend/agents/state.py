import operator
from typing import Annotated, Optional
from typing_extensions import TypedDict


def merge_warnings(previous: list[str], incoming: list[str]) -> list[str]:
    return list(dict.fromkeys([*previous, *incoming]))


class ResearchState(TypedDict, total=False):
    task_id: str
    sources: list[str]
    output_language: str
    _run_context: object
    paper_claims: list[dict]
    paper_chunks: list[dict]
    chunks: list[dict]
    draft_version: int
    analysis_findings: list[dict]
    structured_report: dict
    citations: list[dict]
    warnings: Annotated[list[str], merge_warnings]
    search_diagnostics: list[dict]
    agent_trace: list[dict]
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
    finalization_agents: list[str]
    status: str
    finish_reason: str
    max_papers: int
    writer_finish_reason: str
    writer_generation_attempts: int
    writer_incomplete: bool

    previous_queries: list[str]
    search_review: dict
    search_gaps: list[str]
    search_feedback: str
    retrieval_exhausted: bool
