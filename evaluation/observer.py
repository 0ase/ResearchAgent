"""Optional observation outside backend code; never changes model inputs/outputs."""
from __future__ import annotations

import asyncio
import codecs
from contextvars import ContextVar
from functools import wraps
import json
import logging
from pathlib import Path
import re
import time
import uuid

from evaluation.collect import ROOT, RESEARCH_PATHS, atomic_json, number, query_digest, result_summary, utc_now

active_recorder: ContextVar[Recorder | None] = ContextVar("evaluation_recorder", default=None)


def field(value, key):
    return value.get(key) if isinstance(value, dict) else getattr(value, key, None)


class Recorder:
    def __init__(self, retrieval_top_k: int = 6):
        self.run_id = uuid.uuid4().hex
        self.started = time.perf_counter()
        self.data = {"schema_version": 1, "kind": "observed", "run_id": self.run_id,
                     "started_at": utc_now(), "request_id": None, "session_id": None,
                     "query_hash": None, "task_started": False, "status": "incomplete",
                     "usage_observed": True, "retrieval_observed": True,
                     "retrieval_top_k": retrieval_top_k, "llm_calls": [], "embedding_calls": [],
                     "stage_events": [], "application_retry": False, "degraded": False, "result": {}}
        self.retrievals = {}
        self.failed_stage_ids = set()

    def context(self, context):
        for key in ("request_id", "session_id"):
            if isinstance(context.get(key), str):
                self.data[key] = context[key]

    def model_call(self, kind, kwargs, result, elapsed, status, stage=None):
        usage = field(result, "usage")
        call = {"call_id": uuid.uuid4().hex, "model": str(kwargs.get("model") or "")[:160],
                "stage": stage, "status": status, "duration_seconds": round(elapsed, 6),
                "prompt_tokens": number(field(usage, "prompt_tokens")),
                "completion_tokens": number(field(usage, "completion_tokens")),
                "total_tokens": number(field(usage, "total_tokens"))}
        self.data[kind + "_calls"].append(call)

    def vector_result(self, operation, kwargs, result):
        where = kwargs.get("where") or {}
        paper = where.get("paper_id") if isinstance(where, dict) else None
        if not isinstance(paper, str) or not isinstance(result, dict):
            return
        ids, docs = result.get("ids") or [], result.get("documents") or []
        if operation == "query":
            ids = ids[0] if ids and isinstance(ids[0], list) else []
            docs = docs[0] if docs and isinstance(docs[0], list) else []
            if not docs:
                return  # The real reader uses its prior get() fallback in this case.
            k = kwargs.get("n_results", self.data["retrieval_top_k"])
        else:
            k = min(self.data["retrieval_top_k"], len(docs))
        available = len(ids) == len(docs) and all(isinstance(item, str) and item for item in ids)
        self.retrievals[paper] = {"paper_id": paper, "ids": ids[:k] if available else [],
                                  "ids_available": available, "requested_k": k,
                                  "method": "vector" if operation == "query" else "fallback"}

    def event(self, payload):
        if not isinstance(payload, dict):
            return
        self.context(payload)
        event = payload.get("event")
        if event in {"agent", "stage", "done"}:
            self.data["task_started"] = True
        if event == "done":
            self.data["result"] = result_summary(payload)
            self.data["status"] = "completed" if self.data["result"]["has_report"] else "failed"
            self.data["degraded"] |= bool(self.data["result"]["warning_count"] or self.data["result"]["writer_incomplete"])
        elif event == "error":
            self.data["status"] = "failed"
            self.data["error_code"] = str(payload.get("code") or "SSE_ERROR")[:80]

    def finish(self, directory: Path):
        self.data.update({"ended_at": utc_now(), "server_elapsed_seconds": round(time.perf_counter() - self.started, 6),
                          "retrievals": list(self.retrievals.values())})
        atomic_json(directory / (self.run_id + ".json"), self.data)


class BackendEvents(logging.Handler):
    """Only structural events and numbers; no prompts, exception text or secrets."""
    def __init__(self, context_provider):
        super().__init__()
        self.context_provider = context_provider

    def emit(self, record):
        recorder = active_recorder.get()
        if recorder is None:
            return
        try:
            context = self.context_provider()
            recorder.context(context)
            event = record.getMessage()
            fields = getattr(record, "fields", {})
            stage = context.get("stage")
            if event == "stage.started":
                recorder.data["task_started"] = True
            if event in {"stage.started", "stage.completed", "stage.cancelled", "stage.degraded", "stage.failed"} and stage:
                if event == "stage.failed" and fields.get("error_id") in recorder.failed_stage_ids:
                    return
                recorder.data["stage_events"].append({"stage": stage, "event": event, "duration_ms": number(fields.get("duration_ms"))})
                if event == "stage.failed":
                    recorder.failed_stage_ids.add(fields.get("error_id"))
            elif event in {"analysis.output.failed", "analysis.input.failed", "analysis.request.failed"} and stage:
                error_id = fields.get("error_id")
                if error_id not in recorder.failed_stage_ids:
                    recorder.failed_stage_ids.add(error_id)
                    recorder.data["stage_events"].append({"stage": stage, "event": "stage.failed", "duration_ms": None})
            if event == "stage.degraded":
                recorder.data["degraded"] = True
            if event == "research.cancelled" and recorder.data["status"] != "completed":
                recorder.data["status"] = "cancelled"
            if event in {"screening.batch.retry_split", "analysis.output.retrying", "embedding.attempt.failed"}:
                recorder.data["application_retry"] = True
        except Exception:
            recorder.data["usage_observed"] = False
            recorder.data["retrieval_observed"] = False


def model_wrapper(original, kind, context_provider):
    @wraps(original)
    async def call(resource, *args, **kwargs):
        recorder = active_recorder.get()
        if recorder is None:
            return await original(resource, *args, **kwargs)
        started = time.perf_counter()
        try:
            stage = context_provider().get("stage")
        except Exception:
            stage = None
            recorder.data["usage_observed"] = False
        try:
            result = await original(resource, *args, **kwargs)
        except BaseException:
            # A lost response has unknown billable usage, not zero tokens.
            try:
                recorder.model_call(kind, kwargs, None, time.perf_counter() - started, "failed", stage)
            except Exception:
                recorder.data["usage_observed"] = False
            raise
        try:
            recorder.model_call(kind, kwargs, result, time.perf_counter() - started, "completed", stage)
        except Exception:
            recorder.data["usage_observed"] = False
        return result
    return call


def vector_wrapper(original, operation, context_provider):
    @wraps(original)
    def call(resource, *args, **kwargs):
        result = original(resource, *args, **kwargs)
        recorder = active_recorder.get()
        if recorder is not None and context_provider().get("stage") == "read":
            try:
                recorder.vector_result(operation, kwargs, result)
            except Exception:
                recorder.data["retrieval_observed"] = False
        return result
    return call


def install_observers(chat_class, embedding_class, collection_class, context_provider):
    """Used only by the optional app process, not ordinary backend startup."""
    restores = []
    for cls, method, wrapper in (
        (chat_class, "create", lambda original: model_wrapper(original, "llm", context_provider)),
        (embedding_class, "create", lambda original: model_wrapper(original, "embedding", context_provider)),
        (collection_class, "get", lambda original: vector_wrapper(original, "get", context_provider)),
        (collection_class, "query", lambda original: vector_wrapper(original, "query", context_provider)),
    ):
        original = getattr(cls, method)
        if getattr(original, "_bigone_evaluation", False):
            continue
        replacement = wrapper(original)
        replacement._bigone_evaluation = True
        setattr(cls, method, replacement)
        restores.append((cls, method, original))
    handler = BackendEvents(context_provider)
    logging.getLogger("backend").addHandler(handler)

    def restore():
        logging.getLogger("backend").removeHandler(handler)
        for cls, method, original in restores:
            setattr(cls, method, original)
    return restore


class SSEObserver:
    def __init__(self, callback):
        self.decoder = codecs.getincrementaldecoder("utf-8")()
        self.buffer = ""
        self.callback = callback

    def feed(self, chunk: bytes, final=False):
        self.buffer += self.decoder.decode(chunk, final=final)
        while match := re.search(r"\r?\n\r?\n", self.buffer):
            frame, self.buffer = self.buffer[:match.start()], self.buffer[match.end():]
            self.frame(frame)
        if final and self.buffer.strip():
            self.frame(self.buffer)
            self.buffer = ""

    def frame(self, frame):
        data = "\n".join(line[5:].lstrip(" ") for line in frame.splitlines() if line.startswith("data:"))
        if data:
            self.callback(json.loads(data))


class ObservedApp:
    def __init__(self, app, directory: Path = ROOT / "evaluation/runs/observed", retrieval_top_k=6):
        self.app, self.directory, self.retrieval_top_k = app, directory, retrieval_top_k

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http" or scope.get("method") != "POST" or scope.get("path", "").rstrip("/") not in RESEARCH_PATHS:
            await self.app(scope, receive, send)
            return
        recorder = Recorder(self.retrieval_top_k)
        token = active_recorder.set(recorder)
        request_body = bytearray()
        json_body = bytearray()
        content_type, status = "", None
        parser = SSEObserver(recorder.event)

        async def observed_receive():
            message = await receive()
            if message.get("type") == "http.request" and len(request_body) < 16384:
                request_body.extend(message.get("body", b""))
            return message

        async def observed_send(message):
            nonlocal content_type, status
            # Forward the original message unmodified, even if observation fails.
            await send(message)
            try:
                if message["type"] == "http.response.start":
                    status = message["status"]
                    headers = dict(message.get("headers", []))
                    content_type = headers.get(b"content-type", b"").decode("ascii", errors="ignore")
                    recorder.data["request_id"] = headers.get(b"x-request-id", b"").decode("ascii", errors="ignore") or recorder.data["request_id"]
                elif message["type"] == "http.response.body":
                    body = message.get("body", b"")
                    if "text/event-stream" in content_type:
                        parser.feed(body, final=not message.get("more_body", False))
                    elif "json" in content_type and len(json_body) < 4 * 1024 * 1024:
                        json_body.extend(body)
            except Exception:
                recorder.data["retrieval_observed"] = False

        try:
            await self.app(scope, observed_receive, observed_send)
            if "json" in content_type:
                try:
                    response = json.loads(json_body)
                    if status and 200 <= status < 300:
                        recorder.event({**response, "event": "done"})
                    else:
                        recorder.data["status"] = "failed"
                except (ValueError, TypeError):
                    pass
        except asyncio.CancelledError:
            if recorder.data["status"] != "completed":
                recorder.data["status"] = "cancelled"
            raise
        except BaseException:
            recorder.data["status"] = "failed"
            raise
        finally:
            try:
                request = json.loads(request_body)
                if isinstance(request, dict) and isinstance(request.get("query"), str):
                    recorder.data["query_hash"] = query_digest(request["query"])
            except (ValueError, TypeError):
                pass
            try:
                recorder.finish(self.directory)
            except Exception:
                logging.getLogger("evaluation").warning("Evaluation snapshot unavailable; original research response unchanged.")
            active_recorder.reset(token)
