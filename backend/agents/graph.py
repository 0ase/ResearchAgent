import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from langgraph.graph import StateGraph, END
from backend.agents.state import ResearchState
from backend.agents.orchestrator import orchestrate
from backend.agents.search import search_papers
from backend.agents.read import read_papers
from backend.agents.analyze import analyze_papers
from backend.agents.synthesize import synthesize_review
from backend.agents.critic import critique_output
from backend.agents.filter import filter_papers


def decide_after_search(state: ResearchState) -> str:
    papers = state.get("raw_papers", [])
    round_num = state.get("search_round", 1)

    if len(papers) >= 5:
        return "enough"
    elif round_num >= 3:
        if len(papers) == 0:
            return "no_results"
        return "enough"
    else:
        return "not_enough"


def decide_approval(state: ResearchState) -> str:
    critique = state.get("critique", {})
    if critique.get("approved", True):
        return "approved"
    if state.get("critique_round", 0) >= 2:
        return "approved"
    return "rejected"


def build_graph() -> StateGraph:
    graph = StateGraph(ResearchState)

    graph.add_node("orchestrate", orchestrate)
    graph.add_node("search", search_papers)
    graph.add_node("read", read_papers)
    graph.add_node("analyze", analyze_papers)
    graph.add_node("synthesize", synthesize_review)
    graph.add_node("filter", filter_papers)
    graph.add_node("critic", critique_output)

    # entry
    graph.set_entry_point("orchestrate")

    # pipeline
    graph.add_edge("orchestrate", "search")
    graph.add_conditional_edges("search", decide_after_search, {
        "enough": "filter",
        "not_enough": "search",
        "no_results": END,
    })
    graph.add_edge("filter", "read")
    graph.add_edge("read", "analyze")
    graph.add_edge("analyze", "synthesize")
    graph.add_edge("synthesize", "critic")
    graph.add_conditional_edges("critic", decide_approval, {
        "approved": END,
        "rejected": "synthesize",
    })

    return graph.compile()


async def main():
    app = build_graph()
    result = await app.ainvoke({"user_query": "测试:Transformer注意力机制最新进展"})
    print("✅ 图跑通了！")
    print(f"研究计划: {result['research_plan']}")
    print(f"论文列表: {result['raw_papers']}")
    print(f"搜索轮数: {result['search_round']}")
    print(f"\n📝 答案摘要:")
    print(result.get("final_answer", "暂无")[:500])


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
