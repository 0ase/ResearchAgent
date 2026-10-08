"""Structured logs and context shared by HTTP, SSE and concurrent agents."""
import asyncio
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
from functools import wraps
import inspect
import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import re
import time
import uuid

_context: ContextVar[dict] = ContextVar("log_context", default={})
logger = logging.getLogger("backend")


def current_context() -> dict:
    return dict(_context.get())


@contextmanager
def log_context(**fields):
    token = _context.set({**_context.get(), **fields})
    try:
        yield
    finally:
        _context.reset(token)


class JsonFormatter(logging.Formatter):
    def __init__(self, secrets=()):
        super().__init__()
        self.secrets = tuple(secret for secret in secrets if secret)

    def redact(self, value: str) -> str:
        for secret in self.secrets:
            value = value.replace(secret, "[REDACTED]")
        value = re.sub(r"(?i)(bearer\s+)\S+", r"\1[REDACTED]", value)
        value = re.sub(
            r"(?i)((?:api[_-]?key|token|password|secret)=)[^\s&\"']+",
            r"\1[REDACTED]", value,
        )
        # HTTP SDK exceptions often include URLs with keys, email and queries.
        return re.sub(r"(https?://[^\s?\"']+)\?[^\s\"']+", r"\1?[REDACTED]", value)

    def format(self, record: logging.LogRecord) -> str:
        data = {
            "timestamp": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "process_id": record.process,
            **getattr(record, "trace_context", {}),
            **getattr(record, "fields", {}),
        }
        if record.exc_info:
            data["exception"] = self.formatException(record.exc_info)
        if record.stack_info:
            data["stack"] = record.stack_info

        def clean(value):
            if isinstance(value, str):
                return self.redact(value)
            if isinstance(value, dict):
                return {key: clean(item) for key, item in value.items()}
            if isinstance(value, (list, tuple)):
                return [clean(item) for item in value]
            return value

        return json.dumps(clean(data), ensure_ascii=False, default=str)


class ContextFilter(logging.Filter):
    def filter(self, record):
        record.trace_context = current_context()
        return True


def configure_logging(settings):
    """Replace only our own handlers; keep test runners and server handlers."""
    root = logging.getLogger()
    for handler in list(root.handlers):
        if getattr(handler, "_bigone_handler", False):
            root.removeHandler(handler)
            handler.close()
    root.setLevel(settings.log_level)
    secrets = [
        getattr(settings, name) for name in type(settings).model_fields
        if name.endswith("api_key")
    ]
    formatter = JsonFormatter(secrets)
    log_dir = Path(settings.log_dir)
    if not log_dir.is_absolute():
        log_dir = Path(__file__).resolve().parents[2] / log_dir
    log_dir.mkdir(parents=True, exist_ok=True)
    handlers = [
        logging.StreamHandler(),
        RotatingFileHandler(
            log_dir / "backend.log", maxBytes=settings.log_max_bytes,
            backupCount=settings.log_backup_count, encoding="utf-8",
        ),
    ]
    for handler in handlers:
        handler._bigone_handler = True
        handler.setFormatter(formatter)
        handler.addFilter(ContextFilter())
        root.addHandler(handler)
    # SDK request logs can contain query text; enable explicitly for diagnosis.
    for name in ("httpx", "httpcore", "openai", "anthropic"):
        logging.getLogger(name).setLevel(logging.WARNING)


def report_exception(exc: Exception, event: str, *, level=logging.ERROR, **fields) -> str:
    """Log once per exception, retaining its traceback and chained causes."""
    error_id = getattr(exc, "_bigone_error_id", None)
    if error_id:
        return error_id
    error_id = uuid.uuid4().hex
    exc._bigone_error_id = error_id
    logger.log(
        level, event, exc_info=(type(exc), exc, exc.__traceback__),
        extra={"fields": {**fields, "error_id": error_id, "exception_type": type(exc).__name__}},
    )
    return error_id


def trace_stage(stage: str, function):
    """Keep LangGraph signatures and Command results while tracing each node."""
    def complete(result, started):
        if isinstance(result, dict) and result.get("errors"):
            logger.warning("stage.degraded", extra={"fields": {
                "error_id": uuid.uuid4().hex, "errors": result["errors"],
            }})
        logger.info("stage.completed", extra={"fields": {
            "duration_ms": round((time.perf_counter() - started) * 1000, 2),
        }})
        return result

    if inspect.iscoroutinefunction(function):
        @wraps(function)
        async def run(*args, **kwargs):
            with log_context(stage=stage):
                started = time.perf_counter()
                logger.info("stage.started")
                try:
                    return complete(await function(*args, **kwargs), started)
                except asyncio.CancelledError:
                    logger.info("stage.cancelled")
                    raise
                except Exception as exc:
                    report_exception(exc, "stage.failed")
                    raise
    else:
        @wraps(function)
        def run(*args, **kwargs):
            with log_context(stage=stage):
                started = time.perf_counter()
                logger.info("stage.started")
                try:
                    return complete(function(*args, **kwargs), started)
                except Exception as exc:
                    report_exception(exc, "stage.failed")
                    raise
    return run
