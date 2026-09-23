import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from langgraph.graph import StateGraph, START, END
from backend.agents.state import ResearchState
from backend.agents.analyze import analyze_papers
from backend.agents.synthesize import synthesize_review
from backend.agents.critic import critique_output
from backend.agents.supervisor import supervisor
from backend.agents.retrieval_graph import build_retrieval_graph
from backend.agents.instrumentation import instrument, instrument_supervisor


def finish(state: ResearchState) -> dict:
    from backend.domain.errors import ResearchPipelineError
    from backend.domain.reports import report_has_substantive_body
    if not state.get("paper_insights"):
        raise ResearchPipelineError("NO_READABLE_PAPERS" if state.get("raw_papers") else "NO_RESEARCH_RESULTS")
    draft = state.get("draft_sections") or []
    if not draft:
        raise ResearchPipelineError("EMPTY_REPORT")
    final_answer = state.get("final_answer") or "\n\n".join(item.get("content", "") for item in draft)
    if not report_has_substantive_body(final_answer):
        raise ResearchPipelineError("EMPTY_REPORT")
    return {"status": "completed", "finish_reason": state.get("finish_reason", "研究收尾完成"),
            "final_answer": final_answer,
            "warnings": [] if (state.get("critique") or {}).get("approved") is True else ["CRITIQUE_NOT_APPROVED"]}


def build_graph(run_context=None) -> StateGraph:
    graph = StateGraph(ResearchState)

    graph.add_node("supervisor", instrument_supervisor(supervisor, run_context))
    graph.add_node("retrieval", build_retrieval_graph(run_context))
    graph.add_node("analysis", instrument(analyze_papers, "analyze", run_context))
    graph.add_node("writer", instrument(synthesize_review, "synthesize", run_context))
    graph.add_node("critic", instrument(critique_output, "critic", run_context))
    graph.add_node("finish", finish)

    graph.add_edge(START, "supervisor")

    graph.add_edge("retrieval", "supervisor")
    graph.add_edge("analysis", "supervisor")
    graph.add_edge("writer", "supervisor")
    graph.add_edge("critic", "supervisor")

    graph.add_edge("finish", END)

    return graph.compile()

async def main():
    app = build_graph()
    result = await app.ainvoke({
        "user_query": "2023 年以来 Transformer 注意力机制有哪些最新进展？",
        "search_round": 0,
        "critique_round": 0,
        "step_count": 0,
        "max_steps": 12,
        "status": "running",
        "max_papers": 15,
    })
    print(result.get("final_answer", ""))

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
