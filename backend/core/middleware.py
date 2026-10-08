"""Pure ASGI tracing keeps context active until the last streaming chunk."""
import asyncio
import re
import time
import uuid

from starlette.datastructures import Headers, MutableHeaders

from backend.core.observability import log_context, logger, report_exception


class RequestTraceMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        supplied_id = Headers(scope=scope).get("x-request-id", "")
        request_id = supplied_id if re.fullmatch(r"[A-Za-z0-9._-]{1,128}", supplied_id) else uuid.uuid4().hex
        scope.setdefault("state", {})["request_id"] = request_id
        started = time.perf_counter()
        status = 500
        outcome = "completed"

        async def traced_send(message):
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                MutableHeaders(scope=message)["X-Request-ID"] = request_id
            await send(message)

        with log_context(request_id=request_id, method=scope["method"], path=scope["path"]):
            logger.info("request.started")
            try:
                await self.app(scope, receive, traced_send)
            except asyncio.CancelledError:
                outcome = "cancelled"
                raise
            except Exception as exc:
                outcome = "failed"
                report_exception(exc, "request.failed", status_code=status,
                                 session_id=scope.get("path_params", {}).get("session_id"))
                raise
            finally:
                logger.info("request.completed", extra={"fields": {
                    "status_code": status, "outcome": outcome,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 2),
                }})
