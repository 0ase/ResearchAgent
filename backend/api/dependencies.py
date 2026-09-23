from fastapi import Request

from backend.services.deepseek_settings import DeepSeekSettingsService
from backend.services.task_manager import TaskManager


def get_task_manager(request: Request) -> TaskManager:
    manager = getattr(request.app.state, "task_manager", None)
    if manager is None:
        raise RuntimeError("task manager is not initialized")
    followup = getattr(request.app.state, "followup_manager", None)
    if manager.storage_failed or (followup and followup.storage_failed):
        from backend.api.errors import ApiError
        raise ApiError("STORAGE_UNAVAILABLE", "研究存储暂不可用", status_code=503)
    return manager


def get_deepseek_settings_service(request: Request) -> DeepSeekSettingsService:
    service = getattr(request.app.state, "deepseek_settings_service", None)
    if service is None:
        raise RuntimeError("DeepSeek settings service is not initialized")
    return service
