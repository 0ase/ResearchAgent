from fastapi import APIRouter, Request, Response
from pydantic import BaseModel, Field
from typing import Literal
from backend.api.schemas import FollowUpRequest

router = APIRouter(prefix="/api/v1/research/tasks", tags=["follow-up"])


class ConversationMessage(BaseModel):
    message_id: str
    role: Literal["user", "assistant"]
    content: str
    citations: list[str] = Field(default_factory=list)
    created_at: str


class PendingFollowUp(BaseModel):
    message_id: str
    content: str
    status: Literal["queued", "processing", "failed"]
    error_code: str | None = None
    created_at: str


class ConversationSnapshot(BaseModel):
    task_id: str
    task_status: str
    messages: list[ConversationMessage]
    pending: PendingFollowUp | None = None


@router.get("/{task_id}/messages", response_model=ConversationSnapshot)
async def messages(task_id: str, request: Request):
    return await request.app.state.followup_manager.repository.snapshot(task_id)


@router.put("/{task_id}/follow-up", response_model=ConversationSnapshot)
async def put_followup(task_id: str, body: FollowUpRequest, request: Request):
    manager = request.app.state.followup_manager
    await manager.repository.put(task_id, body.message_id, body.message)
    manager.wake()
    return await manager.repository.snapshot(task_id)


@router.delete("/{task_id}/follow-up", status_code=204)
async def cancel_followup(task_id: str, request: Request):
    await request.app.state.followup_manager.repository.cancel(task_id)
    return Response(status_code=204)
