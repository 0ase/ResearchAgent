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


def finish(state: ResearchState) -> dict:
    draft = state.get("draft_sections", [])

    final_answer = state.get("final_answer", "")
    if not final_answer and draft:
        final_answer = draft[0].get("content", "")
    if not final_answer:
        insights = state.get("paper_insights", [])
        final_answer = "\n\n".join(
            f"**{item.get('source', 'unknown')}**: {item.get('answer', '')}"
            for item in insights
            if item.get("answer")
        )
    if not final_answer:
        papers = state.get("selected_papers") or state.get("raw_papers", [])
        final_answer = "\n\n".join(
            f"### {paper.get('title', 'Untitled')}\n{paper.get('abstract', '')}"
            for paper in papers[:10]
            if paper.get("title") or paper.get("abstract")
        )

    return {
        "status": "completed",
        "finish_reason": state.get(
            "finish_reason",
            "Supervisor 判断研究任务已经完成",
        ),
        "final_answer": final_answer,
    }


def build_graph() -> StateGraph:
    graph = StateGraph(ResearchState)

    graph.add_node("supervisor", supervisor)
    graph.add_node("retrieval", build_retrieval_graph())
    graph.add_node("analysis", analyze_papers)
    graph.add_node("writer", synthesize_review)
    graph.add_node("critic", critique_output)
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
        "max_papers": 10,
    })
    print(result.get("final_answer", ""))

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
