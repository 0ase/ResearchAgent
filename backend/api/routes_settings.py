from fastapi import APIRouter, Depends

from backend.api.dependencies import get_deepseek_settings_service
from backend.api.errors import ApiError
from backend.api.schemas.settings import (
    DeepSeekSettingsResponse,
    UpdateDeepSeekSettingsRequest,
)
from backend.services.deepseek_settings import (
    DeepSeekSettingsService,
    DeepSeekSettingsWriteError,
)


router = APIRouter(prefix="/api/v1/settings/deepseek", tags=["settings"])


@router.get("", response_model=DeepSeekSettingsResponse)
async def get_deepseek_settings(
    service: DeepSeekSettingsService = Depends(get_deepseek_settings_service),
) -> DeepSeekSettingsResponse:
    return service.get()


@router.put("", response_model=DeepSeekSettingsResponse)
async def update_deepseek_settings(
    request: UpdateDeepSeekSettingsRequest,
    service: DeepSeekSettingsService = Depends(get_deepseek_settings_service),
) -> DeepSeekSettingsResponse:
    try:
        return await service.update_api_key(request.api_key)
    except DeepSeekSettingsWriteError as exc:
        raise ApiError(
            "DEEPSEEK_SETTINGS_WRITE_FAILED",
            "无法保存 DeepSeek API Key",
            status_code=500,
            retryable=True,
        ) from exc
