from langgraph.graph import StateGraph, START, END

from backend.agents.state import ResearchState
from backend.agents.orchestrator import orchestrate
from backend.agents.search import search_papers, select_candidate_papers
from backend.agents.filter import filter_papers
from backend.agents.read import read_papers
from backend.agents.search_review import review_search_results
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
        "retrieval_exhausted": False,
    }


def mark_retrieval_exhausted(_: ResearchState) -> dict:
    """标记检索已耗尽，防止主 Supervisor 反复启动同一检索子图。"""
    return {
        "retrieval_exhausted": True,
        "errors": ["达到最大搜索轮次后仍未搜索到论文"],
        "analysis_report": None,
        "draft_sections": [],
        "critique": None,
        "feedback": None,
        "approved": False,
        "final_answer": None,
    }
    
def build_retrieval_graph():
    graph = StateGraph(ResearchState)

    graph.add_node("plan_queries", orchestrate)
    graph.add_node("search", search_papers)
    graph.add_node("review_search", review_search_results)
    graph.add_node("select_candidates", select_candidate_papers)
    graph.add_node("filter", filter_papers)
    graph.add_node("read", read_papers)
    graph.add_node(
        "invalidate_downstream",
        invalidate_downstream,
    )
    graph.add_node("mark_retrieval_exhausted", mark_retrieval_exhausted)

    graph.add_edge(START, "plan_queries")
    graph.add_edge("plan_queries", "search")
    graph.add_edge("search", "review_search")

    graph.add_conditional_edges(
        "review_search",
        route_after_review,
        {
            "enough": "select_candidates",
            "use_existing": "select_candidates",
            "refine": "search",
            "no_results": "mark_retrieval_exhausted",
        },
    )

    graph.add_edge("select_candidates", "filter")
    graph.add_edge("filter", "read")
    graph.add_edge("read", "invalidate_downstream")
    graph.add_edge("invalidate_downstream", END)
    graph.add_edge("mark_retrieval_exhausted", END)

    return graph.compile()

def route_after_review(state: ResearchState) -> str:
    review = state.get("search_review") or {}
    action = review.get("action", "enough")
    papers = state.get("raw_papers", [])
    search_round = state.get("search_round", 0)

    if action == "refine":
        # 防止 Review Agent 绕过最大轮次
        if search_round >= settings.max_search_rounds:
            return "use_existing" if papers else "no_results"

        new_plan = state.get("research_plan", [])

        # 必须真的存在新查询，才能继续搜索
        if new_plan:
            return "refine"

        return "use_existing" if papers else "no_results"

    if action == "no_results":
        return "no_results"

    if action == "use_existing":
        return "use_existing" if papers else "no_results"

    # action == enough
    return "enough" if papers else "no_results"
