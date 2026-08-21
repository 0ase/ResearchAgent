from fastapi import APIRouter, Depends, Response, status

from backend.api.dependencies import get_task_manager
from backend.api.errors import ApiError
from backend.api.schemas.tasks import (
    CreateResearchTaskRequest,
    CreateTaskResponse,
    TaskLinks,
    TaskSnapshot,
    UpdateTaskRequest,
)
from backend.services.task_manager import (
    ActiveTaskError,
    TaskManager,
    TaskNotFoundError,
)

router = APIRouter(prefix="/api/v1/research/tasks", tags=["research tasks"])


@router.post("", response_model=CreateTaskResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_task(
    request: CreateResearchTaskRequest,
    manager: TaskManager = Depends(get_task_manager),
) -> CreateTaskResponse:
    try:
        task = await manager.create_task(request)
    except ActiveTaskError as exc:
        raise ApiError(
            "ACTIVE_TASK_EXISTS",
            "已有研究任务正在运行",
            status_code=409,
            details={"task_id": exc.task.id},
        ) from exc
    return _create_response(task)


@router.get("/active", response_model=TaskSnapshot, responses={204: {"description": "No active task"}})
async def get_active_task(
    manager: TaskManager = Depends(get_task_manager),
):
    task = await manager.tasks.get_active()
    if task is None:
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    return task


@router.get("/{task_id}", response_model=TaskSnapshot)
async def get_task(
    task_id: str,
    manager: TaskManager = Depends(get_task_manager),
) -> TaskSnapshot:
    task = await manager.get_task(task_id)
    if task is None:
        raise _not_found(task_id)
    return task


@router.post("/{task_id}/cancel", response_model=TaskSnapshot, status_code=status.HTTP_202_ACCEPTED)
async def cancel_task(
    task_id: str,
    manager: TaskManager = Depends(get_task_manager),
) -> TaskSnapshot:
    try:
        return await manager.cancel_task(task_id)
    except TaskNotFoundError as exc:
        raise _not_found(task_id) from exc


@router.post("/{task_id}/retry", response_model=TaskSnapshot, status_code=status.HTTP_202_ACCEPTED)
async def retry_task(
    task_id: str,
    manager: TaskManager = Depends(get_task_manager),
) -> TaskSnapshot:
    try:
        return await manager.retry_task(task_id)
    except TaskNotFoundError as exc:
        raise _not_found(task_id) from exc
    except ActiveTaskError as exc:
        raise ApiError(
            "TASK_IS_ACTIVE",
            "活动任务不能重试",
            status_code=409,
            details={"task_id": exc.task.id},
        ) from exc


@router.patch("/{task_id}", response_model=TaskSnapshot)
async def update_task(
    task_id: str,
    request: UpdateTaskRequest,
    manager: TaskManager = Depends(get_task_manager),
) -> TaskSnapshot:
    try:
        return await manager.rename_task(task_id, request.title)
    except TaskNotFoundError as exc:
        raise _not_found(task_id) from exc


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: str,
    manager: TaskManager = Depends(get_task_manager),
) -> Response:
    try:
        await manager.delete_task(task_id)
    except TaskNotFoundError as exc:
        raise _not_found(task_id) from exc
    except ActiveTaskError as exc:
        raise ApiError(
            "TASK_IS_ACTIVE",
            "活动任务不能删除",
            status_code=409,
            details={"task_id": exc.task.id},
        ) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _create_response(task: TaskSnapshot) -> CreateTaskResponse:
    base = f"/api/v1/research/tasks/{task.id}"
    return CreateTaskResponse(
        task=task,
        links=TaskLinks(
            self=base,
            events=f"{base}/events",
            result=f"{base}/result",
        ),
    )


def _not_found(task_id: str) -> ApiError:
    return ApiError(
        "TASK_NOT_FOUND",
        "研究任务不存在",
        status_code=404,
        details={"task_id": task_id},
    )
