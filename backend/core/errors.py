"""Public error contract. Internal exception details stay in server logs."""
import uuid
import sqlite3

import httpx
from openai import APIConnectionError, APIStatusError, APITimeoutError

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from backend.core.observability import current_context, log_context, logger, report_exception


class AppError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 500):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.trace_context = current_context()


class VectorStoreUnavailable(AppError):
    def __init__(self):
        super().__init__(
            "VECTOR_STORE_UNAVAILABLE",
            "向量库进程异常退出或超时，请使用 BIGONE 环境重启后端，并提供追踪编号排查。",
            503,
        )


def error_payload(exc: Exception, *, request_id: str | None = None) -> dict:
    """Also used after SSE headers have been sent; HTTP status stays 200."""
    details = None
    if isinstance(exc, AppError):
        code, message, status = exc.code, exc.message, exc.status_code
    elif isinstance(exc, RequestValidationError):
        code, message, status = "VALIDATION_ERROR", "请求参数不合法，请检查输入。", 422
        # Pydantic input/ctx can contain user text, keys or non-serializable values.
        details = [{"loc": list(e["loc"]), "type": e["type"], "msg": "参数值不合法。"} for e in exc.errors()]
    elif isinstance(exc, HTTPException):
        status = exc.status_code
        code = {404: "NOT_FOUND", 409: "CONFLICT", 405: "METHOD_NOT_ALLOWED"}.get(status, "HTTP_ERROR")
        message = str(exc.detail) if status < 500 else "服务暂时不可用，请稍后重试。"
    elif isinstance(exc, (httpx.TimeoutException, APITimeoutError)):
        code, message, status = "UPSTREAM_TIMEOUT", "外部服务响应超时，请稍后重试。", 504
    elif isinstance(exc, (httpx.HTTPError, APIConnectionError, APIStatusError)):
        code, message, status = "UPSTREAM_UNAVAILABLE", "外部服务暂时不可用，请稍后重试。", 502
    elif isinstance(exc, sqlite3.Error):
        code, message, status = "STORAGE_UNAVAILABLE", "数据存储暂时不可用，请稍后重试。", 503
    else:
        code, message, status = "INTERNAL_ERROR", "服务内部错误，请提供追踪编号以便排查。", 500

    if status >= 500:
        error_id = report_exception(exc, "request.failed", error_code=code, status_code=status,
                                    request_id=request_id or current_context().get("request_id"))
    else:
        error_id = uuid.uuid4().hex
        logger.warning("request.rejected", extra={"fields": {
            "error_id": error_id, "error_code": code, "status_code": status,
        }})
    payload = {
        "code": code, "message": message, "status_code": status,
        "request_id": request_id or current_context().get("request_id"), "error_id": error_id,
    }
    if details is not None:
        payload["details"] = details
    return payload


async def handle_error(request: Request, exc: Exception):
    with log_context(**getattr(exc, "trace_context", {})):
        payload = error_payload(exc, request_id=getattr(request.state, "request_id", None))
    headers = dict(exc.headers or {}) if isinstance(exc, HTTPException) else {}
    headers["X-Request-ID"] = payload["request_id"] or ""
    return JSONResponse(
        {"error": payload, "detail": payload.get("details", payload["message"])},
        status_code=payload["status_code"], headers=headers,
    )


def register_error_handlers(app):
    for exception_type in (AppError, HTTPException, RequestValidationError, Exception):
        app.add_exception_handler(exception_type, handle_error)
