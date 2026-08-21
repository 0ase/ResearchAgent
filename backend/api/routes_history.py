from fastapi import APIRouter, Depends, Query

from backend.api.dependencies import get_task_manager
from backend.api.schemas.tasks import TaskSnapshot
from backend.services.task_manager import TaskManager

router = APIRouter(prefix="/api/v1/research", tags=["research history"])


@router.get("/history", response_model=list[TaskSnapshot])
async def research_history(
    limit: int = Query(default=20, ge=1, le=100),
    manager: TaskManager = Depends(get_task_manager),
) -> list[TaskSnapshot]:
    return await manager.tasks.list_history(limit)
