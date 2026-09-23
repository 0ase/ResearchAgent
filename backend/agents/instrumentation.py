"""Project internal dynamic nodes onto the stable, public seven-stage contract."""
import inspect
import time

from backend.api.schemas.events import EventType
from backend.api.schemas.tasks import ResearchStage
from backend.domain.errors import ResearchPipelineError
from backend.services.task_runner import _stage_metrics


def instrument(node, stage_name, context):
    if context is None:
        return node

    async def run(state):
        stage = ResearchStage(stage_name)
        started = time.perf_counter()
        await context.stage_started(stage)
        try:
            result = node(state)
            if inspect.isawaitable(result):
                result = await result
            context.raise_if_cancelled()
            await context.stage_progress(stage, _stage_metrics(stage_name, result or {}))
            warnings = (result or {}).get("warnings", [])
            if warnings:
                await context._append(EventType.STAGE_WARNING, stage=stage, payload={"warnings": [safe_text(w) for w in warnings]})
            artifact = {"orchestrate": ("research_plan", EventType.PLAN_AVAILABLE),
                "search": ("raw_papers", EventType.PAPERS_DISCOVERED),
                "filter": ("selected_papers", EventType.PAPERS_SELECTED),
                "analyze": ("analysis_report", EventType.ANALYSIS_AVAILABLE),
                "synthesize": ("draft_sections", EventType.DRAFT_AVAILABLE),
                "critic": ("critique", EventType.CRITIQUE_COMPLETED)}.get(stage_name)
            if artifact and (result or {}).get(artifact[0]):
                value = result[artifact[0]]
                await context._append(artifact[1], stage=stage, payload={"count": len(value), "attempt": context.attempts[stage.value]})
            if stage_name == "read":
                await context.stage_progress(stage, {"metrics": {"papersRead": len((result or {}).get("paper_insights", []))}})
            await context.stage_completed(stage, started, {"legacy": legacy_stage_payload(stage_name, {**state, **(result or {})})})
            return result
        except Exception as exc:
            await context.stage_failed(stage, exc.code if isinstance(exc, ResearchPipelineError) else "INTERNAL_ERROR")
            raise
    return run


def instrument_supervisor(node, context):
    async def run(state):
        if context:
            context.raise_if_cancelled()
        command = await node(state)
        update = command.update or {}
        # No raw provider responses or exception strings enter public telemetry.
        payload = {
            "step": int(update.get("step_count", 0)),
            "next_agent": str(update.get("next_agent", "finish")),
            "objective": safe_text(update.get("current_task")),
            "reason": safe_text(update.get("decision_reason")),
        }
        update["agent_trace"] = [*state.get("agent_trace", []), payload]
        if context and context.event_recorder:
            context.raise_if_cancelled()
            await context.event_recorder.append(task_id=context.task_id,
                event_type=EventType.AGENT_DELEGATED, payload=payload)
        return command
    return run


def safe_text(value):
    from backend.config import settings
    text = str(value or "")
    for key in (settings.deepseek_api_key, settings.openai_api_key, settings.dashscope_api_key):
        if key:
            text = text.replace(key, "[redacted]")
    return text[:2000]


def legacy_stage_payload(stage, state):
    """Compatibility projection only; it never owns graph execution or storage."""
    papers = state.get("raw_papers", [])
    insights = state.get("paper_insights", [])
    analysis = state.get("analysis_report") or {}
    if stage == "orchestrate":
        return {"sub_queries": [p.get("display_query") or p.get("sub_query", "") for p in state.get("research_plan", [])]}
    if stage == "search":
        return {"total": len(papers), "papers_preview": papers[:30],
            **{label: sum(p.get("source") == source for p in papers) for label, source in (("arxiv","arxiv"),("s2","semantic_scholar"),("pubmed","pubmed"),("crossref","crossref"))}}
    if stage == "filter":
        return {"count": len(state.get("selected_papers", [])), "papers": state.get("selected_papers", [])}
    if stage == "read":
        return {"papers_read": len(insights), "preview": str(insights[0].get("answer", ""))[:300] if insights else ""}
    if stage == "analyze":
        return {key: len(analysis.get(key, [])) for key in ("agreements", "contradictions", "gaps")}
    if stage == "synthesize":
        text = state.get("final_answer") or ""
        return {"length": len(text), "preview": text[:300]}
    return {"score": (state.get("critique") or {}).get("score"), "approved": state.get("approved", False)}
