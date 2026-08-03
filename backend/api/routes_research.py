import json
import uuid
from typing import Any

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from backend.agents.graph import build_graph
from backend.api.schemas import ResearchRequest, ResearchResponse
from backend.services.session_store import save_session, get_sessions, get_session


router = APIRouter(prefix="/research", tags=["research"])

# 阶段→中文标签
STAGE_LABELS = {
    "orchestrate": "🧠 拆解研究问题",
    "search": "🔍 4源搜论文",
    "filter": "📑 筛选论文",
    "read": "📖 阅读论文",
    "analyze": "🔬 跨论文对比分析",
    "synthesize": "✍️ 撰写文献综述",
    "critic": "✅ 质量评审",
}

DEFAULT_MAX_STEPS = 12


def _initial_state(req: ResearchRequest) -> dict[str, Any]:
    """为普通调用和流式调用提供一致的工作流初始状态。"""
    return {
        "user_query": req.query,
        "search_round": 0,
        "critique_round": 0,
        "step_count": 0,
        "max_steps": DEFAULT_MAX_STEPS,
        "status": "running",
        "max_papers": req.max_papers,
    }


def _paper_payload(paper: dict) -> dict:
    return {
        "title": paper.get("title", ""),
        "authors": paper.get("authors", []),
        "abstract": paper.get("abstract", ""),
        "pdf_url": paper.get("pdf_url", ""),
        "source": paper.get("source", ""),
        "source_id": paper.get("source_id", ""),
        "published_date": str(paper.get("published_date", "")),
        "citation_count": paper.get("citation_count", 0),
        "relevance_score": paper.get("relevance_score", 0),
        "relevance_reason": paper.get("relevance_reason", ""),
    }


def _signature(value: Any) -> str:
    """生成稳定签名，用于识别同一阶段在多轮调用中的真实变化。"""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _collect_stage_events(
    state: dict,
    signatures: dict[str, str],
) -> list[dict]:
    """将状态变化转换为兼容现有前端的阶段事件。"""
    events: list[dict] = []

    def append_if_changed(key: str, value: Any, payload: dict) -> None:
        if not value:
            signatures.pop(key, None)
            return
        new_signature = _signature(value)
        if signatures.get(key) == new_signature:
            return
        signatures[key] = new_signature
        events.append(payload)

    plan = state.get("research_plan", [])
    append_if_changed("plan", plan, {
        "stage": "orchestrate",
        "label": STAGE_LABELS["orchestrate"],
        "sub_queries": [task.get("sub_query", "") for task in plan],
    })

    papers = state.get("raw_papers", [])
    append_if_changed("papers", papers, {
        "stage": "search",
        "label": STAGE_LABELS["search"],
        "total": len(papers),
        "arxiv": sum(1 for p in papers if p.get("source") == "arxiv"),
        "s2": sum(1 for p in papers if p.get("source") == "semantic_scholar"),
        "pubmed": sum(1 for p in papers if p.get("source") == "pubmed"),
        "crossref": sum(1 for p in papers if p.get("source") == "crossref"),
        "papers_preview": [_paper_payload(p) for p in papers[:30]],
    })

    selected = state.get("selected_papers", [])
    append_if_changed("selected", selected, {
        "stage": "filter",
        "label": STAGE_LABELS["filter"],
        "count": len(selected),
        "papers": [_paper_payload(p) for p in selected],
    })

    insights = state.get("paper_insights", [])
    append_if_changed("insights", insights, {
        "stage": "read",
        "label": STAGE_LABELS["read"],
        "papers_read": len(insights),
        "preview": insights[0].get("answer", "")[:300] if insights else "",
    })

    analysis = state.get("analysis_report")
    append_if_changed("analysis", analysis, {
        "stage": "analyze",
        "label": STAGE_LABELS["analyze"],
        "agreements": len(analysis.get("agreements", [])) if isinstance(analysis, dict) else 0,
        "contradictions": len(analysis.get("contradictions", [])) if isinstance(analysis, dict) else 0,
        "gaps": len(analysis.get("gaps", [])) if isinstance(analysis, dict) else 0,
    })

    draft = state.get("draft_sections", [])
    content = draft[0].get("content", "") if draft else ""
    append_if_changed("draft", draft, {
        "stage": "synthesize",
        "label": STAGE_LABELS["synthesize"],
        "length": len(content),
        "preview": content[:300],
    })

    critique = state.get("critique")
    append_if_changed("critique", critique, {
        "stage": "critic",
        "label": STAGE_LABELS["critic"],
        "score": critique.get("score", "?") if isinstance(critique, dict) else "?",
        "approved": critique.get("approved", False) if isinstance(critique, dict) else False,
        "issue_type": critique.get("issue_type", "") if isinstance(critique, dict) else "",
        "round": state.get("critique_round", 0),
    })

    return events


def _result_payload(state: dict, agent_trace: list[dict] | None = None) -> dict:
    papers = [_paper_payload(p) for p in state.get("raw_papers", [])]
    return {
        "final_answer": state.get("final_answer") or "",
        "critique": state.get("critique"),
        "papers": papers,
        "paper_insights": state.get("paper_insights", []),
        "analysis": state.get("analysis_report") or {},
        "agent_trace": agent_trace or [],
        "finish_reason": state.get("finish_reason", ""),
    }


@router.post("/", response_model=ResearchResponse)
async def start_research(req: ResearchRequest):
    """普通模式：一次性返回完整结果"""
    app = build_graph()
    result = await app.ainvoke(_initial_state(req))
    papers = result.get("raw_papers", [])
    session_id = str(uuid.uuid4())
    payload = _result_payload(result)
    try:
        await save_session(session_id=session_id, query=req.query, result=payload)
    except Exception as exc:
        print(f"[SessionStore] Save failed: {exc}")

    return ResearchResponse(
        session_id=session_id,
        research_plan=result.get("research_plan", []),
        papers_count=len(papers),
        final_answer=result.get("final_answer") or "Research Done",
    )


@router.post("/stream")
async def start_research_stream(req: ResearchRequest):
    """流式模式: SSE 实时推送每个阶段的进度和数据"""

    async def event_stream():
        try:
            app = build_graph()
            final_state: dict | None = None
            signatures: dict[str, str] = {}
            last_step = -1
            agent_trace: list[dict] = []

            async for namespace, state in app.astream(
                _initial_state(req),
                stream_mode="values",
                subgraphs=True,
            ):
                if not namespace:
                    final_state = state

                step = state.get("step_count", 0)
                next_agent = state.get("next_agent", "")
                if next_agent and step != last_step:
                    last_step = step
                    delegation = {
                        "step": step,
                        "agent": "supervisor",
                        "next_agent": next_agent,
                        "objective": state.get("current_task", ""),
                        "reason": state.get("decision_reason", ""),
                    }
                    agent_trace.append(delegation)
                    yield _sse("agent", delegation)

                for stage_event in _collect_stage_events(state, signatures):
                    yield _sse("stage", stage_event)

            # ---- async for 结束后 ----
            if final_state is None:
                yield _sse("error", {"message": "研究工作流没有产生任何状态。"})
                return

            session_id = str(uuid.uuid4())
            final_papers = final_state.get("raw_papers", [])

            # 搜索阶段结束后，如果一篇论文都没搜到 → 提前终止，不跑后续无用阶段
            if not final_papers:
                yield _sse("error", {
                    "message": (
                        "未搜到任何论文。可能原因：① 网络无法访问学术 API；"
                        "② 研究问题过于冷门；③ API 超时。请检查网络或尝试其他问题。"
                    ),
                })
                return

            result_payload = _result_payload(final_state, agent_trace)
            yield _sse("done", {**result_payload, "session_id": session_id})

            # 保存到历史记录（失败不影响主流程）
            try:
                await save_session(
                    session_id=session_id,
                    query=req.query,
                    result=result_payload,
                )
            except Exception as e:
                print(f"[SessionStore] Save failed: {e}")

        except Exception as e:
            yield _sse("error", {"message": str(e)})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
    )


def _sse(event: str, data: dict) -> str:
    """格式化 SSE 消息"""
    payload = {**data, "event": event}
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


@router.get("/history")
async def research_history(limit: int = 20):
    """获取历史研究记录列表"""
    sessions = await get_sessions(limit)
    return sessions


@router.get("/{session_id}")
async def research_detail(session_id: str):
    """获取某次研究的完整结果"""
    session = await get_session(session_id)
    if session is None:
        from fastapi.responses import JSONResponse
        return JSONResponse({"error": "session not found"}, status_code=404)
    return session
