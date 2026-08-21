import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import asyncio
import time

from langgraph.graph import StateGraph, END
from backend.agents.state import ResearchState
from backend.agents.orchestrator import orchestrate
from backend.agents.search import search_papers
from backend.agents.read import read_papers
from backend.agents.analyze import analyze_papers
from backend.agents.synthesize import synthesize_review
from backend.agents.critic import critique_output
from backend.agents.filter import filter_papers
from backend.domain.errors import ResearchPipelineError
from backend.api.schemas.tasks import ResearchStage
from backend.services.run_context import ResearchRunContext


def decide_after_search(state: ResearchState) -> str:
    papers = state.get("raw_papers", [])
    round_num = state.get("search_round", 1)

    max_papers = max(1, state.get("max_papers", 5))
    if len(papers) >= min(max_papers, 5):
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


def build_graph(run_context: ResearchRunContext | None = None) -> StateGraph:
    graph = StateGraph(ResearchState)

    graph.add_node("orchestrate", _instrument("orchestrate", orchestrate, run_context))
    graph.add_node("search", _instrument("search", search_papers, run_context))
    graph.add_node("read", _instrument("read", read_papers, run_context))
    graph.add_node("analyze", _instrument("analyze", analyze_papers, run_context))
    graph.add_node("synthesize", _instrument("synthesize", synthesize_review, run_context))
    graph.add_node("filter", _instrument("filter", filter_papers, run_context))
    graph.add_node("critic", _instrument("critic", critique_output, run_context))
    graph.add_node("fail_no_results", _raise_no_research_results)

    # entry
    graph.set_entry_point("orchestrate")

    # pipeline
    graph.add_edge("orchestrate", "search")
    graph.add_conditional_edges("search", decide_after_search, {
        "enough": "filter",
        "not_enough": "search",
        "no_results": "fail_no_results",
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


def _raise_no_research_results(_state: ResearchState) -> dict:
    raise ResearchPipelineError("NO_RESEARCH_RESULTS")


def _instrument(name: str, node, context: ResearchRunContext | None):
    if context is None:
        return node

    stage = ResearchStage(name)

    async def wrapped(state: ResearchState):
        context.raise_if_cancelled()
        started_at = time.perf_counter()
        await context.stage_started(stage)
        await context.stage_progress(stage, {"status": "running"})
        try:
            result = await node(state)
            context.raise_if_cancelled()
            counts = _stage_metrics(name, result or {})
            await context.stage_progress(stage, counts)
            await context.stage_completed(stage, started_at)
            return result
        except asyncio.CancelledError:
            raise
        except ResearchPipelineError as exc:
            await context.stage_failed(stage, exc.code)
            raise
        except Exception:
            await context.stage_failed(stage)
            raise

    return wrapped


def _stage_metrics(node_name: str, node_state: dict) -> dict:
    counts: dict[str, int] = {}
    for key in [
        "sub_queries",
        "raw_papers",
        "selected_papers",
        "paper_insights",
        "paper_claims",
        "analysis_findings",
    ]:
        value = node_state.get(key)
        if isinstance(value, list):
            counts[key] = len(value)
    metrics = {"stage": node_name, "counts": counts}
    if node_name == "search":
        metrics["source_stats"] = _source_stats(node_state.get("search_diagnostics", []))
    return metrics


def _source_stats(diagnostics: list[dict]) -> dict[str, dict[str, int]]:
    stats: dict[str, dict[str, int]] = {}
    for item in diagnostics:
        source = str(item.get("source") or "unknown")
        bucket = stats.setdefault(source, {"papers": 0, "queries": 0, "errors": 0})
        bucket["papers"] += int(item.get("papers") or 0)
        bucket["queries"] += 1
        if item.get("status") == "error":
            bucket["errors"] += 1
    return stats


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
