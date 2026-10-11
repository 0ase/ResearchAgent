"""Loopback-only settings endpoints; research routing remains untouched."""
import asyncio
import ipaddress
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, Request

from backend.api.settings_schemas import SettingsUpdate
from backend.core.errors import AppError
from backend.services.settings_store import get_settings_snapshot, save_settings_update

router = APIRouter(prefix="/settings", tags=["settings"])


def _local_host(host: str | None) -> bool:
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host or "").is_loopback
    except ValueError:
        return False


def require_local_settings_access(request: Request):
    try:
        host = urlsplit(f"http://{request.headers.get('host', '')}").hostname
        origin = request.headers.get("origin")
        parsed = urlsplit(origin) if origin else None
    except ValueError:
        raise AppError("SETTINGS_ORIGIN_REJECTED", "配置请求来源不受信任。", 403) from None
    if not request.client or not _local_host(request.client.host) or not _local_host(host):
        raise AppError("SETTINGS_LOCAL_ONLY", "配置管理仅允许在本机访问。", 403)
    if parsed:
        if parsed.scheme not in {"http", "https"} or not _local_host(parsed.hostname):
            raise AppError("SETTINGS_ORIGIN_REJECTED", "配置请求来源不受信任。", 403)
    if request.method == "PUT" and (not origin or request.headers.get("x-b1gone-config") != "local"):
        raise AppError("SETTINGS_ORIGIN_REJECTED", "请使用本机前端设置页保存配置。", 403)


@router.get("", dependencies=[Depends(require_local_settings_access)])
async def read_settings():
    return await asyncio.to_thread(get_settings_snapshot)


@router.put("", dependencies=[Depends(require_local_settings_access)])
async def update_settings(update: SettingsUpdate):
    return await asyncio.to_thread(save_settings_update, update)
