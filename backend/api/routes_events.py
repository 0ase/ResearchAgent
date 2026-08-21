from __future__ import annotations

import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, Header, Query, Request
from fastapi.responses import StreamingResponse

from backend.api.dependencies import get_task_manager
from backend.api.errors import ApiError
from backend.api.schemas.events import EventType, ResearchEvent
from backend.api.schemas.tasks import TaskStatus
from backend.config import settings
from backend.services.event_recorder import EventRecorder
from backend.services.task_manager import TaskManager

router = APIRouter(
    prefix="/api/v1/research/tasks/{task_id}",
    tags=["research events"],
)

TERMINAL_EVENT_TYPES = {
    EventType.TASK_COMPLETED,
    EventType.TASK_FAILED,
    EventType.TASK_CANCELLED,
    EventType.TASK_INTERRUPTED,
}


def get_event_recorder(request: Request) -> EventRecorder:
    recorder = getattr(request.app.state, "event_recorder", None)
    if recorder is None:
        raise RuntimeError("event recorder is not initialized")
    return recorder


@router.get("/events")
async def stream_events(
    task_id: str,
    after: int = Query(default=0, ge=0),
    last_event_id: str | None = Header(default=None, alias="Last-Event-ID"),
    manager: TaskManager = Depends(get_task_manager),
    recorder: EventRecorder = Depends(get_event_recorder),
) -> StreamingResponse:
    task = await manager.get_task(task_id)
    if task is None:
        raise ApiError(
            "TASK_NOT_FOUND",
            "研究任务不存在",
            status_code=404,
            details={"task_id": task_id},
        )

    cursor = max(after, _parse_last_event_id(last_event_id))

    async def event_stream() -> AsyncIterator[str]:
        nonlocal cursor
        while True:
            events = await recorder.list_events_after(task_id, cursor)
            if events:
                for event in events:
                    cursor = event.sequence
                    yield _format_event(event)
                    if event.event_type in TERMINAL_EVENT_TYPES:
                        return
                continue

            current = await manager.get_task(task_id)
            if current is None or current.status in {
                TaskStatus.COMPLETED,
                TaskStatus.FAILED,
                TaskStatus.CANCELLED,
                TaskStatus.INTERRUPTED,
            }:
                return

            changed = await recorder.wait_for_event(
                task_id,
                after_sequence=cursor,
                timeout=settings.event_keepalive_seconds,
            )
            if not changed:
                yield ": keepalive\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


def _format_event(event: ResearchEvent) -> str:
    return (
        f"id: {event.sequence}\n"
        f"event: {event.event_type.value}\n"
        f"data: {json.dumps(event.model_dump(mode='json'), ensure_ascii=False)}\n\n"
    )


def _parse_last_event_id(value: str | None) -> int:
    if not value:
        return 0
    try:
        return max(0, int(value))
    except ValueError:
        return 0
