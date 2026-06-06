import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from langgraph.graph import StateGraph, END
from backend.agents.state import ResearchState
from backend.agents.search import search_papers
from backend.agents.orchestrator import orchestrate


# async def orchestrate(state: ResearchState) -> dict:
#     """占位：后续实现任务拆解"""
#     query = state["user_query"]
#     return {
#         "research_plan": [{"sub_query": query, "status": "pending"}],
#         "search_round": 1
#     }

def decide_after_search(state: ResearchState) -> str:
    papers = state.get("raw_papers", []) # "[]"代表默认变量，如果没有任何的论文，那么就从一个空列表开始
    round_num = state.get("search_round", 1)

    if len(papers) >= 5:
        return "enough"
    elif round_num >= 3:
        return "enough"
    else:
        return "not_enough"

def build_graph() -> StateGraph:
    graph = StateGraph(ResearchState)
    graph.add_node("orchestrate", orchestrate)
    graph.add_node("search", search_papers)

    graph.set_entry_point("orchestrate") # 设定起始边
    graph.add_edge("orchestrate", "search")
    graph.add_conditional_edges("search", decide_after_search, 
        {
            "enough": END,
            "not_enough": "search",
        }
    )

    return graph.compile()

async def main():
    app = build_graph()
    result = await app.ainvoke({"user_query": "测试:Transformer注意力机制最新进展"})
    print("✅ 图跑通了！")
    print(f"研究计划:{result["research_plan"]}")
    print(f"论文列表:{result["raw_papers"]}")
    print(f"搜索轮数:{result["search_round"]}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

