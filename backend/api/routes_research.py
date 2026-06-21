import json
import uuid
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from backend.agents.graph import build_graph
from backend.api.schemas import ResearchRequest, ResearchResponse

router = APIRouter(prefix="/research", tags=["research"])

# 阶段→中文标签
STAGE_LABELS = {
    "orchestrate": "🧠 拆解研究问题",
    "search": "🔍 4源搜论文",
    "read": "📖 阅读论文",
    "analyze": "🔬 跨论文对比分析",
    "synthesize": "✍️ 撰写文献综述",
    "critic": "✅ 质量评审",
}


@router.post("/", response_model=ResearchResponse)
async def start_research(req: ResearchRequest):
    """普通模式：一次性返回完整结果"""
    app = build_graph()
    result = await app.ainvoke({
        "user_query": req.query,
        "search_round": 0,
    })
    papers = result.get("raw_papers", [])
    return ResearchResponse(
        session_id=str(uuid.uuid4()),
        research_plan=result.get("research_plan", []),
        papers_count=len(papers),
        final_answer=result.get("final_answer", "Research Done"),
    )


@router.post("/stream")
async def start_research_stream(req: ResearchRequest):
    """流式模式: SSE 实时推送每个阶段的进度和数据"""

    async def event_stream():
        try:
            app = build_graph()
            seen = set()

            async for state in app.astream(
                {"user_query": req.query, "search_round": 0, "max_papers": req.max_papers},
                stream_mode="values",
            ):
                plan = state.get("research_plan", [])
                papers = state.get("raw_papers", [])
                insights = state.get("paper_insights", [])
                analysis = state.get("analysis_report")
                draft = state.get("draft_sections", [])
                critique = state.get("critique")

                if plan and "plan" not in seen:
                    seen.add("plan")
                    yield _sse("stage", {
                        "stage": "orchestrate",
                        "label": STAGE_LABELS["orchestrate"],
                        "sub_queries": [t.get("sub_query", "") for t in plan],
                    })

                if papers and "papers" not in seen:
                    seen.add("papers")
                    arxiv = sum(1 for p in papers if p.get("source") == "arxiv")
                    s2 = sum(1 for p in papers if p.get("source") == "semantic_scholar")
                    pubmed = sum(1 for p in papers if p.get("source") == "pubmed")
                    crossref = sum(1 for p in papers if p.get("source") == "crossref")
                    yield _sse("stage", {
                        "stage": "search",
                        "label": STAGE_LABELS["search"],
                        "total": len(papers),
                        "arxiv": arxiv, "s2": s2, "pubmed": pubmed, "crossref": crossref,
                    })

                if insights and "insights" not in seen:
                    seen.add("insights")
                    yield _sse("stage", {
                        "stage": "read",
                        "label": STAGE_LABELS["read"],
                        "papers_read": len(insights),
                        "preview": insights[0].get("answer", "")[:300] if insights else "",
                    })

                if analysis and isinstance(analysis, dict) and "analysis" not in seen:
                    seen.add("analysis")
                    yield _sse("stage", {
                        "stage": "analyze",
                        "label": STAGE_LABELS["analyze"],
                        "agreements": len(analysis.get("agreements", [])),
                        "contradictions": len(analysis.get("contradictions", [])),
                        "gaps": len(analysis.get("gaps", [])),
                    })

                if draft and "draft" not in seen:
                    seen.add("draft")
                    content = draft[0].get("content", "") if draft else ""
                    yield _sse("stage", {
                        "stage": "synthesize",
                        "label": STAGE_LABELS["synthesize"],
                        "length": len(content),
                        "preview": content[:300],
                    })

                if critique and isinstance(critique, dict) and "critique" not in seen:
                    seen.add("critique")
                    yield _sse("stage", {
                        "stage": "critic",
                        "label": STAGE_LABELS["critic"],
                        "score": critique.get("score", "?"),
                        "approved": critique.get("approved", False),
                    })

            # async for 结束后推送最终结果
            final = state.get("final_answer", "") if state else ""
            yield _sse("done", {
                "final_answer": final,
                "critique": state.get("critique") if state else None,
            })

        except Exception as e:
            yield _sse("error", {"message": str(e)})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
    )


def _sse(event: str, data: dict) -> str:
    """格式化 SSE 消息"""
    data["event"] = event  # 把事件类型也塞进数据里
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
