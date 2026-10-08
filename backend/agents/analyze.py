"""Cross-paper analysis with model-response diagnostics and explicit failures."""
import asyncio
import json
import logging
import re
import time
from urllib.parse import urlsplit
import uuid

from openai import AsyncOpenAI
from pydantic import BaseModel, ValidationError

from backend.agents.state import ResearchState
from backend.config import settings
from backend.core.errors import AppError
from backend.core.observability import log_context, logger, report_exception

ANALYSIS_TIMEOUT = 120.0
ANALYSIS_SDK_RETRIES = 2


class AnalysisReport(BaseModel):
    agreements: list[str | dict]
    contradictions: list[str | dict]
    methods: dict
    gaps: list[str | dict]


class AnalysisOutputError(AppError):
    def __init__(self, code: str, message: str, **details):
        super().__init__(code, message, 502)
        self.diagnostic_details = details


def _field(value, name, default=None):
    return value.get(name, default) if isinstance(value, dict) else getattr(value, name, default)


def _content_state(content) -> str:
    if content is None:
        return "missing"
    if not isinstance(content, str):
        return "unexpected_type"
    if not content:
        return "empty"
    return "text" if content.strip() else "whitespace"


def _response_diagnostics(response, max_tokens: int) -> dict:
    choices = _field(response, "choices")
    choice = choices[0] if isinstance(choices, (list, tuple)) and choices else None
    message = _field(choice, "message")
    content = _field(message, "content")
    reasoning = _field(message, "reasoning_content")
    refusal = _field(message, "refusal")
    tools = _field(message, "tool_calls")
    usage = _field(response, "usage")
    completion_tokens = _field(usage, "completion_tokens")
    return {
        "response_id": _field(response, "id"),
        "provider_request_id": _field(response, "_request_id"),
        "response_model": _field(response, "model"),
        "choices_count": len(choices) if isinstance(choices, (list, tuple)) else None,
        "message_present": message is not None,
        "finish_reason": _field(choice, "finish_reason"),
        "content_state": _content_state(content),
        "content_characters": len(content) if isinstance(content, str) else None,
        "content_trimmed_characters": len(content.strip()) if isinstance(content, str) else None,
        "reasoning_content_present": reasoning is not None,
        "reasoning_characters": len(reasoning) if isinstance(reasoning, str) else None,
        "refusal_present": bool(refusal),
        "tool_calls_count": len(tools) if isinstance(tools, (list, tuple)) else 0,
        "usage_available": usage is not None,
        "prompt_tokens": _field(usage, "prompt_tokens"),
        "completion_tokens": completion_tokens,
        "total_tokens": _field(usage, "total_tokens"),
        "reasoning_tokens": _field(_field(usage, "completion_tokens_details"), "reasoning_tokens"),
        "completion_budget_reached": (completion_tokens >= max_tokens
                                      if isinstance(completion_tokens, (int, float)) else None),
    }


def _parse_json(text: str | None) -> dict:
    """Accept plain/fenced JSON; never convert parse failure into empty findings."""
    if not isinstance(text, str):
        raise AnalysisOutputError("ANALYSIS_INVALID_RESPONSE", "跨论文分析返回了无效响应，请提供追踪编号排查。",
                                  failure_kind="invalid_content_type")
    text = text.strip()
    if not text:
        raise AnalysisOutputError("ANALYSIS_EMPTY_RESPONSE", "跨论文分析未返回正文，请提供追踪编号排查。",
                                  failure_kind="empty_final_answer")
    candidates = [text]
    for pattern in (r"```(?:json)?\s*(\{.*?\})\s*```", r"\{.*\}"):
        match = re.search(pattern, text, re.DOTALL)
        if match:
            candidates.append(match.group(1) if match.lastindex else match.group(0))
    last_error = None
    for candidate in candidates:
        try:
            data = json.loads(candidate)
        except json.JSONDecodeError as exc:
            last_error = exc
            continue
        try:
            report = AnalysisReport.model_validate(data)
        except ValidationError as exc:
            # Pydantic's exception text includes input values; keep only locations/types.
            problems = [{"loc": list(error["loc"]), "type": error["type"]}
                        for error in exc.errors(include_input=False, include_context=False)]
            raise AnalysisOutputError("ANALYSIS_INVALID_SCHEMA", "跨论文分析结果字段不完整或类型不正确，请提供追踪编号排查。",
                                      failure_kind="invalid_analysis_schema", schema_errors=problems) from None
        return report.model_dump()
    raise AnalysisOutputError("ANALYSIS_INVALID_JSON", "跨论文分析结果无法解析为 JSON，请提供追踪编号排查。",
                              failure_kind="invalid_json", json_error=last_error.msg if last_error else None,
                              json_error_line=last_error.lineno if last_error else None,
                              json_error_column=last_error.colno if last_error else None,
                              json_error_position=last_error.pos if last_error else None)


def _request_options(api_host: str | None, attempt: int) -> tuple[dict, dict]:
    """Only send DeepSeek-specific controls to its documented API host."""
    if not api_host or not (api_host == "deepseek.com" or api_host.endswith(".deepseek.com")):
        return {}, {"thinking_setting": "provider_default", "reasoning_effort_setting": "provider_default",
                    "response_format_setting": "prompt_only"}
    effort = settings.analysis_thinking_effort if attempt == 1 else "none"
    thinking = "disabled" if effort == "none" else "enabled"
    return {"reasoning_effort": effort, "extra_body": {"thinking": {"type": thinking}},
            "response_format": {"type": "json_object"}}, {
        "thinking_setting": thinking, "reasoning_effort_setting": effort, "response_format_setting": "json_object"}


def _validate_response(response, diagnostics: dict) -> dict:
    if not diagnostics["choices_count"] or not diagnostics["message_present"]:
        raise AnalysisOutputError("ANALYSIS_INVALID_RESPONSE", "跨论文分析返回了无效响应，请提供追踪编号排查。",
                                  failure_kind="missing_choice_or_message")
    if diagnostics["finish_reason"] == "content_filter" or diagnostics["refusal_present"]:
        raise AnalysisOutputError("ANALYSIS_RESPONSE_REJECTED", "跨论文分析未提供可用答案，请提供追踪编号排查。",
                                  failure_kind="response_filtered_or_refused")
    if diagnostics["tool_calls_count"]:
        raise AnalysisOutputError("ANALYSIS_INVALID_RESPONSE", "跨论文分析返回了无效响应，请提供追踪编号排查。",
                                  failure_kind="unexpected_tool_calls")
    content = _field(_field(_field(response, "choices")[0], "message"), "content")
    try:
        if diagnostics["content_state"] in {"missing", "empty", "whitespace"}:
            raise AnalysisOutputError("ANALYSIS_EMPTY_RESPONSE", "跨论文分析未返回正文，请提供追踪编号排查。",
                                      failure_kind="reasoning_without_final_answer"
                                      if (diagnostics["reasoning_characters"] or diagnostics["reasoning_tokens"])
                                      else "empty_final_answer")
        # A complete, schema-valid object is usable even if the service labels its
        # final token 'length'. A partial object is never accepted as an empty report.
        return _parse_json(content)
    except AnalysisOutputError:
        if diagnostics["finish_reason"] == "length":
            raise AnalysisOutputError("ANALYSIS_TRUNCATED", "跨论文分析达到生成长度限制，未获得完整结果，请提供追踪编号排查。",
                                      failure_kind="generation_length_limit") from None
        raise


async def analyze_papers(state: ResearchState) -> dict:
    """Compare usable summaries, with bounded recovery and per-attempt tracing."""
    insights = state.get("paper_insights", [])
    query = state.get("user_query", "")
    objective = state.get("current_task", "")
    model = settings.light_model or settings.default_model
    run_id = uuid.uuid4().hex
    answers = [insight.get("answer") if isinstance(insight.get("answer"), str) else "" for insight in insights]
    sources = [{"paper_index": i + 1, "source_id": insight.get("source"),
                "summary_characters": len(answer), "summary_nonempty": bool(answer.strip())}
               for i, (insight, answer) in enumerate(zip(insights, answers))]
    nonempty = sum(source["summary_nonempty"] for source in sources)
    all_insights = "\n\n".join(f"### Paper {i + 1} [Source {sources[i]['source_id']}]\n{answer}"
                                for i, answer in enumerate(answers) if answer.strip())
    messages = [
        {"role": "system", "content": (
            "You are a research meta-analyst. Analyze the provided paper "
            "summaries and identify: agreements, contradictions, "
            "methodological differences, and research gaps. "
            "Return ONLY valid JSON with these keys: "
            "agreements (list), contradictions (list), "
            "methods (dict: method_name -> list of paper indices), gaps (list). "
            "Use only the supplied evidence and identify supporting paper indices or source IDs. "
            "Different methods are not by themselves contradictory findings. "
            "Keep each list to at most five concise findings, without introductory commentary. "
            "Do not invent findings to fill a category. Example JSON shape: "
            '{"agreements": [], "contradictions": [], "methods": {}, "gaps": []}')},
        {"role": "user", "content": (
            f"Research question: {query}\n"
            f"Current analysis objective: {objective}\n\n"
            f"Paper summaries:\n{all_insights}\n\nReturn JSON analysis.")},
    ]
    base_request = {"analysis_run_id": run_id, "model": model,
                    "api_host": urlsplit(settings.base_url).hostname,
                    "timeout_seconds": ANALYSIS_TIMEOUT, "sdk_max_retries": ANALYSIS_SDK_RETRIES,
                    "input_summaries": len(insights), "nonempty_summaries": nonempty,
                    "empty_summaries": len(insights) - nonempty, "sent_summaries": nonempty, "papers": sources}
    with log_context(stage="analysis", analysis_run_id=run_id):
        if not nonempty:
            error = AnalysisOutputError("ANALYSIS_INPUT_EMPTY", "跨论文分析没有可用的论文摘要，请提供追踪编号排查。",
                                        failure_kind="no_nonempty_paper_summaries")
            report_exception(error, "analysis.input.failed", **base_request, error_code=error.code,
                             **error.diagnostic_details)
            raise error
        if nonempty < len(insights):
            logger.warning("analysis.input.empty_summaries", extra={"fields": {
                "empty_paper_ids": [source["source_id"] for source in sources if not source["summary_nonempty"]],
                "empty_summaries": len(insights) - nonempty}})
        attempts = []
        client = None
        run_started = time.perf_counter()
        retry_codes = {"ANALYSIS_TRUNCATED", "ANALYSIS_EMPTY_RESPONSE", "ANALYSIS_INVALID_JSON",
                       "ANALYSIS_INVALID_SCHEMA", "ANALYSIS_INVALID_RESPONSE"}
        for attempt in range(1, settings.analysis_max_attempts + 1):
            max_tokens = settings.analysis_max_tokens if attempt == 1 else settings.analysis_retry_max_tokens
            options, mode = _request_options(base_request["api_host"], attempt)
            request_messages = list(messages)
            if attempts:
                request_messages.append({"role": "user", "content": (
                    f"The previous attempt failed with {attempts[-1]['error_code']}. "
                    "Return the entire analysis as one complete JSON object with all four required keys. "
                    "Keep findings brief and grounded in the same paper evidence; no additional discussion.")})
            call_id = uuid.uuid4().hex
            request = {**base_request, **mode, "analysis_call_id": call_id, "attempt": attempt,
                       "max_tokens": max_tokens,
                       "input_characters": sum(len(message["content"]) for message in request_messages)}
            with log_context(analysis_call_id=call_id, analysis_attempt=attempt):
                logger.info("analysis.request.started", extra={"fields": request})
                started = time.perf_counter()
                try:
                    if client is None:
                        client = AsyncOpenAI(api_key=settings.llm_api_key, base_url=settings.base_url,
                                             timeout=ANALYSIS_TIMEOUT, max_retries=ANALYSIS_SDK_RETRIES)
                    response = await client.chat.completions.create(model=model, max_tokens=max_tokens,
                                                                   messages=request_messages, **options)
                except asyncio.CancelledError:
                    logger.info("analysis.request.cancelled")
                    raise
                except Exception as exc:
                    report_exception(exc, "analysis.request.failed", **request,
                                     duration_ms=round((time.perf_counter() - started) * 1000, 2),
                                     provider_request_id=getattr(exc, "request_id", None),
                                     http_status=getattr(exc, "status_code", None))
                    raise
                diagnostics = {**request, **_response_diagnostics(response, max_tokens),
                               "duration_ms": round((time.perf_counter() - started) * 1000, 2)}
                logger.info("analysis.response.received", extra={"fields": diagnostics})
                try:
                    analysis = _validate_response(response, diagnostics)
                except AnalysisOutputError as exc:
                    retry = attempt < settings.analysis_max_attempts and exc.code in retry_codes
                    error_id = report_exception(exc, "analysis.output.retrying" if retry else "analysis.output.failed",
                                                level=logging.WARNING if retry else logging.ERROR,
                                                **diagnostics, error_code=exc.code,
                                                **exc.diagnostic_details)
                    attempts.append({**diagnostics, "status": "retrying" if retry else "failed",
                                     "error_code": exc.code, "error_id": error_id})
                    if retry:
                        continue
                    raise
                counts = {key: len(analysis[key]) for key in ("agreements", "contradictions", "methods", "gaps")}
                if diagnostics["finish_reason"] == "length":
                    logger.warning("analysis.output.complete_at_limit", extra={"fields": diagnostics})
                attempts.append({**diagnostics, "status": "completed"})
                diagnostics.update({"status": "completed", "counts": counts,
                                    "empty_analysis": not any(counts.values()), "attempts": attempts,
                                    "attempts_count": attempt, "recovered": attempt > 1,
                                    "total_duration_ms": round((time.perf_counter() - run_started) * 1000, 2)})
                logger.info("analysis.completed", extra={"fields": {**diagnostics, **counts}})
                return {"analysis_report": analysis, "analysis_diagnostics": diagnostics,
                        "draft_sections": [], "critique": None, "approved": False}
