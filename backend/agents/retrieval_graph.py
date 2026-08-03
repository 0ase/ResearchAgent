from langgraph.graph import StateGraph, START, END

from backend.agents.state import ResearchState
from backend.agents.orchestrator import orchestrate
from backend.agents.search import search_papers
from backend.agents.filter import filter_papers
from backend.agents.read import read_papers
from backend.config import settings


def invalidate_downstream(_: ResearchState) -> dict:
    """新证据会使旧分析、旧草稿和旧评审失效。"""
    return {
        "analysis_report": None,
        "draft_sections": [],
        "critique": None,
        "feedback": None,
        "approved": False,
        "final_answer": None,
    }

def decide_after_search(state: ResearchState) -> str:
    papers = state.get("raw_papers", [])
    round_num = state.get("search_round", 0)

    if len(papers) >= settings.min_paper_default:
        return "enough"
    
    if round_num >= settings.max_search_rounds:
        return "stop"
    
    return "retry"

def build_retrieval_graph():
    graph = StateGraph(ResearchState)

    graph.add_node("plan_queries", orchestrate)
    graph.add_node("search", search_papers)
    graph.add_node("filter", filter_papers)
    graph.add_node("read", read_papers)
    graph.add_node("invalidate_downstream", invalidate_downstream)

    graph.add_edge(START, "plan_queries")
    graph.add_edge("plan_queries", "search")

    graph.add_conditional_edges(
        "search",
        decide_after_search,
        {
            "enough": "filter",
            "retry": "search",
            "stop": "invalidate_downstream",
        }
    )

    graph.add_edge("filter", "read")
    graph.add_edge("read", "invalidate_downstream")
    graph.add_edge("invalidate_downstream", END)

    return graph.compile()
