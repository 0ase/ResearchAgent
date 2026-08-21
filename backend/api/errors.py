from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ApiError(Exception):
    """A safe, client-facing application error."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        status_code: int = 400,
        retryable: bool = False,
        details: Any | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.retryable = retryable
        self.details = details


class ErrorDetail(BaseModel):
    code: str
    message: str
    retryable: bool = False
    details: Any | None = None
    request_id: str = Field(min_length=1)


class ErrorEnvelope(BaseModel):
    error: ErrorDetail


def _request_id(request: Request) -> str:
    return request.headers.get("X-Request-ID") or str(uuid.uuid4())


def _response(
    request: Request,
    *,
    status_code: int,
    code: str,
    message: str,
    retryable: bool = False,
    details: Any | None = None,
) -> JSONResponse:
    payload = ErrorEnvelope(
        error=ErrorDetail(
            code=code,
            message=message,
            retryable=retryable,
            details=details,
            request_id=_request_id(request),
        )
    ).model_dump(exclude_none=True)
    return JSONResponse(status_code=status_code, content=payload)


def install_error_handlers(app) -> None:
    @app.exception_handler(ApiError)
    async def handle_api_error(request: Request, exc: ApiError) -> JSONResponse:
        return _response(
            request,
            status_code=exc.status_code,
            code=exc.code,
            message=exc.message,
            retryable=exc.retryable,
            details=exc.details,
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        return _response(
            request,
            status_code=422,
            code="VALIDATION_ERROR",
            message="请求参数无效",
            details=_safe_validation_errors(exc),
        )

    @app.exception_handler(Exception)
    async def handle_unknown_error(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled request error", exc_info=exc)
        return _response(
            request,
            status_code=500,
            code="INTERNAL_ERROR",
            message="服务器内部错误",
        )


def _safe_validation_errors(exc: RequestValidationError) -> list[dict[str, Any]]:
    safe_errors: list[dict[str, Any]] = []
    for error in exc.errors():
        safe_error = {
            key: value
            for key, value in error.items()
            if key not in {"input", "ctx"}
        }
        context = error.get("ctx")
        if isinstance(context, dict):
            safe_error["ctx"] = {
                key: str(value)
                for key, value in context.items()
            }
        safe_errors.append(safe_error)
    return safe_errors
