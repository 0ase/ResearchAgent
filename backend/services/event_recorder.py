from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any

from backend.api.schemas.events import EventLevel, EventType, ResearchEvent
from backend.api.schemas.tasks import ResearchStage
from backend.repositories.event_repository import EventRepository


class EventRecorder:
    """Durable event writer that wakes SSE subscribers after commit."""

    def __init__(self, repository: EventRepository) -> None:
        self.repository = repository
        self._conditions: defaultdict[str, asyncio.Condition] = defaultdict(
            asyncio.Condition
        )

    async def append(
        self,
        *,
        task_id: str,
        event_type: EventType,
        stage: ResearchStage | None = None,
        level: EventLevel = EventLevel.INFO,
        payload: dict[str, Any] | None = None,
        schema_version: int = 1,
    ) -> ResearchEvent:
        event = await self.repository.append(
            task_id=task_id,
            event_type=event_type,
            stage=stage,
            level=level,
            payload=payload,
            schema_version=schema_version,
        )
        condition = self._conditions[task_id]
        async with condition:
            condition.notify_all()
        return event

    async def list_events_after(
        self,
        task_id: str,
        after_sequence: int = 0,
    ) -> list[ResearchEvent]:
        return await self.repository.list_events_after(task_id, after_sequence)

    async def wait_for_event(
        self,
        task_id: str,
        *,
        after_sequence: int,
        timeout: float | None,
    ) -> bool:
        condition = self._conditions[task_id]
        async with condition:
            if await self.repository.latest_sequence(task_id) > after_sequence:
                return True
            try:
                if timeout is None:
                    await condition.wait()
                else:
                    await asyncio.wait_for(condition.wait(), timeout=timeout)
            except asyncio.TimeoutError:
                return False
            return True
