"""Streamlit compatibility transport over the canonical task lifecycle."""
import asyncio
import json
import uuid
import re
from fastapi import APIRouter, Request, Query
from fastapi.responses import StreamingResponse
from backend.api.errors import ApiError
from backend.api.schemas import ResearchRequest, ResearchResponse, FollowUpRequest, FollowUpResponse
from backend.api.schemas.tasks import CreateResearchTaskRequest, ResearchTaskOptions
from backend.domain.tasks import is_terminal
from backend.services.task_manager import ActiveTaskError

router = APIRouter(prefix="/research", tags=["research"])
STAGE_LABELS = {
    "orchestrate": "🧠 拆解研究问题",
    "search": "🔍 4源搜论文",
    "filter": "📑 筛选论文",
    "read": "📖 阅读论文",
    "analyze": "🔬 跨论文对比分析",
    "synthesize": "✍️ 撰写文献综述",
    "critic": "✅ 质量评审",
}


async def _create(req, request):
    manager = request.app.state.task_manager
    try:
        task = await manager.create_task(CreateResearchTaskRequest(
            client_request_id=str(uuid.uuid4()), query=req.query,
            options=ResearchTaskOptions(max_papers=req.max_papers)))
    except ActiveTaskError as exc:
        raise ApiError("ACTIVE_TASK_EXISTS", "An active task already exists", status_code=409, details={"task_id": exc.task.id})
    return manager, task

def _legacy(result):
    return {**result.model_dump(mode="json"), **result.run_metadata,
            "final_answer": _legacy_markdown(result.report_markdown, result)}


def _legacy_markdown(markdown, result):
    citations = _legacy_citation_sources(result)
    return re.sub(r"\[\[CITE:([^\]]+)\]\]", lambda m: f"[Source {citations[m[1]]}]" if citations.get(m[1]) else "[unverified citation]", markdown)


def _legacy_citation_sources(result):
    papers = {p.get("paper_id"): p.get("source_id") or p.get("paper_id") for p in result.papers}
    return {c.get("citation_id"): papers.get(c.get("paper_id")) for c in result.citations if c.get("valid")}

async def _wait_result(manager, task_id):
    while True:
        task = await manager.get_task(task_id)
        if task is None:
            raise ApiError("TASK_NOT_FOUND", "Task not found", status_code=404)
        if is_terminal(task.status):
            result = await manager.results.get(task_id)
            if task.status.value != "completed" or result is None:
                raise ApiError(task.error_code or "RESEARCH_FAILED", "Research did not complete", status_code=422)
            return result
        await asyncio.sleep(0.1)

@router.post("/", response_model=ResearchResponse)
async def start_research(req: ResearchRequest, request: Request):
    manager, task = await _create(req, request)
    result = await _wait_result(manager, task.id)
    return ResearchResponse(session_id=task.id, research_plan=result.research_plan,
        papers_count=len(result.papers), final_answer=_legacy_markdown(result.report_markdown, result))

@router.post("/stream")
async def start_research_stream(req: ResearchRequest, request: Request):
    manager, task = await _create(req, request)
    async def events():
        cursor = 0
        while True:
            batch = await manager.events.list_events_after(task.id, cursor)
            for event in batch:
                cursor = event.sequence
                if event.event_type.value == "agent.delegated":
                    yield _sse("agent", event.payload)
                elif event.stage and event.event_type.value in {"stage.started", "stage.completed"}:
                    yield _sse("stage", {"stage": event.stage.value,
                        "label": STAGE_LABELS[event.stage.value], **event.payload.get("legacy", event.payload)})
                if event.event_type.value == "task.completed":
                    result = await manager.results.get(task.id)
                    yield _sse("done", {**_legacy(result), "session_id": task.id})
                    return
                if event.event_type.value in {"task.failed","task.cancelled","task.interrupted"}:
                    yield _sse("error", {"message": "Research did not complete", **event.payload})
                    return
            yield ": keepalive\n\n"
            await asyncio.sleep(0.5)
    return StreamingResponse(events(), media_type="text/event-stream",
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"})

def _sse(event, data):
    return f"data: {json.dumps({**data, 'event': event}, ensure_ascii=False)}\n\n"

@router.get("/history")
async def research_history(request: Request, limit: int = Query(20, ge=1, le=100)):
    tasks = await request.app.state.task_manager.tasks.list_history(limit)
    return [{"session_id": t.id, "query": t.query, "created_at": t.created_at,
             "papers_count": t.statistics.get("papers_count", 0),
             "score": t.statistics.get("critique_score", "")} for t in tasks]

@router.get("/{session_id}")
async def research_detail(session_id: str, request: Request):
    manager = request.app.state.task_manager
    task = await manager.get_task(session_id)
    if task is None:
        raise ApiError("TASK_NOT_FOUND", "Task not found", status_code=404)
    result = await manager.results.get(session_id)
    return {"session_id": task.id, "query": task.query, "created_at": task.created_at,
            "result": _legacy(result) if result else {}}

@router.get("/{session_id}/messages")
async def research_messages(session_id: str, request: Request, limit: int = Query(50, ge=1, le=200)):
    snapshot = await request.app.state.followup_manager.repository.snapshot(session_id)
    result = await request.app.state.task_manager.results.get(session_id)
    citations = _legacy_citation_sources(result) if result else {}
    return [{**m, "session_id": session_id,
        "content": _legacy_markdown(m["content"], result) if result and m["role"] == "assistant" else m["content"],
        "citations": [citations.get(c) or c for c in m["citations"]]}
        for m in snapshot["messages"][-limit:]]

@router.post("/{session_id}/chat", response_model=FollowUpResponse)
async def followup_chat(session_id: str, req: FollowUpRequest, request: Request):
    manager = request.app.state.followup_manager
    await manager.repository.put(session_id, req.message_id, req.message)
    manager.wake()
    while True:
        snapshot = await manager.repository.snapshot(session_id)
        for message in snapshot["messages"]:
            if message["message_id"] == req.message_id and message["role"] == "assistant":
                result = await manager.results.get(session_id)
                citations = _legacy_citation_sources(result) if result else {}
                return FollowUpResponse(session_id=session_id,
                    answer=_legacy_markdown(message["content"], result) if result else message["content"],
                    citations=[citations.get(c) or c for c in message["citations"]], mode="answer_from_context")
        pending = snapshot["pending"]
        if not pending or pending["message_id"] != req.message_id or pending["status"] == "failed":
            raise ApiError("FOLLOWUP_UNAVAILABLE", "Follow-up could not complete", status_code=409)
        await asyncio.sleep(0.1)
