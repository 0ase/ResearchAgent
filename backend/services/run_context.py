from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any

from backend.api.schemas.events import EventLevel, EventType
from backend.api.schemas.tasks import ResearchStage


@dataclass(slots=True)
class ResearchRunContext:
    task_id: str
    event_recorder: object
    cancel_event: asyncio.Event

    def raise_if_cancelled(self) -> None:
        if self.cancel_event.is_set():
            raise asyncio.CancelledError

    async def stage_started(self, stage: ResearchStage) -> None:
        self.raise_if_cancelled()
        await self._append(EventType.STAGE_STARTED, stage=stage)

    async def stage_progress(
        self,
        stage: ResearchStage,
        payload: dict[str, Any] | None = None,
    ) -> None:
        self.raise_if_cancelled()
        await self._append(
            EventType.STAGE_PROGRESS,
            stage=stage,
            payload=payload or {},
        )

    async def stage_completed(
        self,
        stage: ResearchStage,
        started_at: float,
        payload: dict[str, Any] | None = None,
    ) -> None:
        await self._append(
            EventType.STAGE_COMPLETED,
            stage=stage,
            payload={
                "duration_ms": max(0, int((time.perf_counter() - started_at) * 1000)),
                **(payload or {}),
            },
        )

    async def stage_failed(
        self,
        stage: ResearchStage,
        code: str = "INTERNAL_ERROR",
    ) -> None:
        await self._append(
            EventType.STAGE_FAILED,
            stage=stage,
            level=EventLevel.ERROR,
            payload={"code": code},
        )

    async def _append(
        self,
        event_type: EventType,
        *,
        stage: ResearchStage,
        level: EventLevel = EventLevel.INFO,
        payload: dict[str, Any] | None = None,
    ) -> None:
        if self.event_recorder is None:
            return
        append = getattr(self.event_recorder, "append")
        await append(
            task_id=self.task_id,
            event_type=event_type,
            stage=stage,
            level=level,
            payload=payload or {},
        )


def context_from_state(state: dict[str, Any]) -> ResearchRunContext | None:
    context = state.get("_run_context")
    return context if isinstance(context, ResearchRunContext) else None
