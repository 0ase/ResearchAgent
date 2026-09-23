from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from typing import Any

from backend.agents.state import ResearchState
from backend.api.schemas.events import EventLevel, EventType
from backend.api.schemas.tasks import ResearchStage, TaskSnapshot
from backend.domain.errors import ResearchPipelineError
from backend.services.run_context import ResearchRunContext
from backend.config import current_settings, settings_scope

STAGE_NAMES = {stage.value for stage in ResearchStage}


class TaskRunner:
    """Adapter around LangGraph, instrumented with public progress events."""

    def __init__(
        self,
        graph_factory: Callable[[], Any] | None = None,
        event_recorder: object | None = None,
        configuration=None,
    ) -> None:
        self._graph_factory = graph_factory
        self._event_recorder = event_recorder
        self.configuration = configuration or current_settings()

    async def run(
        self, task: TaskSnapshot, cancel_event: asyncio.Event,
    ) -> dict[str, Any]:
        with settings_scope(self.configuration):
            return await self._run(task, cancel_event)

    async def _run(
        self,
        task: TaskSnapshot,
        cancel_event: asyncio.Event,
    ) -> dict[str, Any]:
        context = ResearchRunContext(
            task_id=task.id,
            event_recorder=self._event_recorder,
            cancel_event=cancel_event,
        )
        graph = self._make_graph(context)
        output_language = task.options.get("output_language")
        if output_language not in {"zh-CN", "en"}:
            output_language = task.effective_locale
        initial_state: ResearchState = {
            "task_id": task.id,
            "user_query": task.query,
            "search_round": 0,
            "max_papers": task.options.get("max_papers", 15),
            "critique_round": 0,
            "step_count": 0,
            "max_steps": 12,
            "status": "running",
            "sources": list(task.options.get("sources", [])),
            "output_language": output_language,
            "_run_context": context,
        }

        if self._graph_factory is not None and hasattr(graph, "astream"):
            final_state: dict[str, Any] = dict(initial_state)
            current_stage: str | None = None
            try:
                async for update in graph.astream(initial_state, stream_mode="updates"):
                    context.raise_if_cancelled()
                    for node_name, node_state in update.items():
                        final_state.update(node_state or {})
                        if node_name in STAGE_NAMES:
                            current_stage = node_name
                            await self._run_stage(context, node_name, node_state or {})
            except asyncio.CancelledError:
                raise
            except ResearchPipelineError as exc:
                if current_stage is not None and self._event_recorder is not None:
                    await self._record_stage_failed(context, current_stage, exc.code)
                raise
            except Exception:
                if current_stage is not None and self._event_recorder is not None:
                    await self._record_stage_failed(context, current_stage)
                raise
            context.raise_if_cancelled()
            return final_state

        context.raise_if_cancelled()
        invocation = asyncio.create_task(graph.ainvoke(initial_state, config={"recursion_limit": 100}))
        cancellation = asyncio.create_task(cancel_event.wait())
        try:
            done, _ = await asyncio.wait({invocation, cancellation}, return_when=asyncio.FIRST_COMPLETED)
            if cancellation in done:
                raise asyncio.CancelledError
            result = await invocation
        finally:
            for pending in (invocation, cancellation):
                if not pending.done():
                    pending.cancel()
            await asyncio.gather(invocation, cancellation, return_exceptions=True)
        context.raise_if_cancelled()
        return result

    def _make_graph(self, context: ResearchRunContext):
        if self._graph_factory is not None:
            return self._graph_factory()
        from backend.agents.graph import build_graph

        return build_graph(run_context=context)

    async def _run_stage(
        self,
        context: ResearchRunContext,
        node_name: str,
        node_state: dict[str, Any],
    ) -> None:
        if self._event_recorder is None:
            return
        stage = ResearchStage(node_name)
        started_at = time.monotonic()
        await self._event_recorder.append(
            task_id=context.task_id,
            event_type=EventType.STAGE_STARTED,
            stage=stage,
            payload={},
        )
        context.raise_if_cancelled()
        await self._event_recorder.append(
            task_id=context.task_id,
            event_type=EventType.STAGE_PROGRESS,
            stage=stage,
            payload=_stage_metrics(node_name, node_state),
        )
        context.raise_if_cancelled()
        await self._event_recorder.append(
            task_id=context.task_id,
            event_type=EventType.STAGE_COMPLETED,
            stage=stage,
            payload={"duration_ms": int((time.monotonic() - started_at) * 1000)},
        )

    async def _record_stage_failed(
        self,
        context: ResearchRunContext,
        node_name: str,
        code: str = "INTERNAL_ERROR",
    ) -> None:
        await self._event_recorder.append(
            task_id=context.task_id,
            event_type=EventType.STAGE_FAILED,
            stage=ResearchStage(node_name),
            level=EventLevel.ERROR,
            payload={"code": code},
        )


def _stage_metrics(node_name: str, node_state: dict[str, Any]) -> dict[str, Any]:
    counts: dict[str, int] = {}
    for key in [
        "sub_queries",
        "raw_papers",
        "selected_papers",
        "paper_insights",
        "paper_claims",
        "analysis_findings",
        "agreements",
        "contradictions",
        "gaps",
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
