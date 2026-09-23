from typing import Literal

from fastapi import APIRouter, Depends, Query, Response

from backend.api.dependencies import get_task_manager
from backend.api.errors import ApiError
from backend.api.schemas.results import ResearchTaskResultResponse
from backend.services.export_service import export_result
from backend.services.task_manager import TaskManager

router = APIRouter(
    prefix="/api/v1/research/tasks/{task_id}",
    tags=["research results"],
)


@router.get("/result", response_model=ResearchTaskResultResponse)
async def get_result(
    task_id: str,
    manager: TaskManager = Depends(get_task_manager),
) -> ResearchTaskResultResponse:
    task = await manager.get_task(task_id)
    if task is None:
        raise _not_found(task_id)
    result = await manager.results.get(task_id)
    if result is None:
        raise ApiError(
            "RESULT_NOT_READY",
            "研究结果尚未准备好",
            status_code=409,
            retryable=task.status.value in {"queued", "running", "cancelling"},
        )
    return ResearchTaskResultResponse.from_legacy(result)


@router.get("/export")
async def export_task(
    task_id: str,
    format: Literal["markdown", "bibtex", "json"] = Query(default="markdown"),
    manager: TaskManager = Depends(get_task_manager),
) -> Response:
    task = await manager.get_task(task_id)
    if task is None:
        raise _not_found(task_id)
    result = await manager.results.get(task_id)
    if result is None:
        raise ApiError("RESULT_NOT_READY", "研究结果尚未准备好", status_code=409)
    content, media_type, extension = export_result(result, format)
    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": (
                f'attachment; filename="research-{task_id}.{extension}"'
            )
        },
    )


def _not_found(task_id: str) -> ApiError:
    return ApiError(
        "TASK_NOT_FOUND",
        "研究任务不存在",
        status_code=404,
        details={"task_id": task_id},
    )
