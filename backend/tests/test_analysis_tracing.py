"""Trace and API contracts for failed versus successfully empty analysis output."""
import asyncio
import json
import logging
import sqlite3
from types import SimpleNamespace

import httpx
from openai import APITimeoutError
import pytest

from backend.agents import analyze
from backend.api import routes_research
from backend.config import settings
from backend.core.errors import error_payload
from backend.core.observability import ContextFilter, JsonFormatter, current_context, log_context, trace_stage
from backend.main import create_app
from scripts import diagnose_analysis

VALID_REPORT = {"agreements": ["共同结论"], "contradictions": [], "methods": {"Method A": 1}, "gaps": ["未解决问题"]}
STATE = {"user_query": "PRIVATE-QUESTION", "current_task": "PRIVATE-OBJECTIVE",
         "paper_insights": [{"source": "paper-1", "answer": "PRIVATE-PAPER-SUMMARY"},
                            {"source": "paper-2", "answer": "   "}]}


def response(content, *, reason="stop", reasoning=None, usage=True):
    return SimpleNamespace(id="provider-response-1", _request_id="provider-http-1", model="test-model",
        choices=[SimpleNamespace(finish_reason=reason, message=SimpleNamespace(
            content=content, reasoning_content=reasoning, refusal=None, tool_calls=None))],
        usage=SimpleNamespace(prompt_tokens=1200, completion_tokens=1500, total_tokens=2700,
                              completion_tokens_details=SimpleNamespace(reasoning_tokens=1500)) if usage else None)


@pytest.fixture
def capture(caplog):
    caplog.set_level(logging.INFO)
    context_filter = ContextFilter()
    caplog.handler.addFilter(context_filter)
    yield caplog
    caplog.handler.removeFilter(context_filter)


def fake_client(monkeypatch, result):
    # Keep the trace-classification cases at the original small budget and disable
    # recovery here; recovery/default configuration has its own behavioral tests.
    monkeypatch.setattr(settings, "analysis_max_tokens", 1500)
    monkeypatch.setattr(settings, "analysis_retry_max_tokens", 1500)
    monkeypatch.setattr(settings, "analysis_max_attempts", 1)
    calls = []
    async def create(**kwargs):
        calls.append(kwargs)
        if isinstance(result, BaseException):
            raise result
        return result
    monkeypatch.setattr(analyze, "AsyncOpenAI", lambda **kwargs: SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))))
    monkeypatch.setattr(settings, "openai_api_key", "test-key")
    return calls


def events(capture, name):
    return [record for record in capture.records if record.message == name]


@pytest.mark.asyncio
async def test_valid_response_logs_input_mapping_and_preserves_diagnostics(monkeypatch, capture):
    calls = fake_client(monkeypatch, response(json.dumps(VALID_REPORT)))
    with log_context(request_id="request-1", session_id="session-1"):
        result = await analyze.analyze_papers(STATE)
    diagnostics = result["analysis_diagnostics"]
    assert result["analysis_report"] == VALID_REPORT
    assert diagnostics["status"] == "completed" and not diagnostics["empty_analysis"]
    assert diagnostics["input_summaries"] == 2 and diagnostics["nonempty_summaries"] == 1
    assert diagnostics["response_id"] == "provider-response-1"
    assert diagnostics["provider_request_id"] == "provider-http-1"
    assert diagnostics["prompt_tokens"] == 1200 and diagnostics["reasoning_tokens"] == 1500
    assert calls[0]["max_tokens"] == 1500
    assert "PRIVATE-PAPER-SUMMARY" in calls[0]["messages"][1]["content"]
    for name in ("analysis.request.started", "analysis.response.received", "analysis.completed"):
        record = events(capture, name)[0]
        assert record.trace_context["request_id"] == "request-1"
        assert record.trace_context["session_id"] == "session-1"
        assert record.trace_context["analysis_call_id"] == diagnostics["analysis_call_id"]
    assert events(capture, "analysis.input.empty_summaries")[0].fields["empty_paper_ids"] == ["paper-2"]
    payload = routes_research._result_payload(result)
    assert payload["analysis_diagnostics"] == diagnostics
    stage = next(e for e in routes_research._collect_stage_events(result, {}) if e["stage"] == "analyze")
    assert stage["diagnostics"]["status"] == "completed" and stage["agreements"] == 1
    formatted = "\n".join(JsonFormatter().format(record) for record in capture.records)
    assert all(private not in formatted for private in ("PRIVATE-QUESTION", "PRIVATE-OBJECTIVE", "PRIVATE-PAPER-SUMMARY"))
    assert current_context() == {}


@pytest.mark.asyncio
async def test_length_limit_with_only_reasoning_is_traceable_and_never_returns_zero_findings(monkeypatch, capture):
    calls = fake_client(monkeypatch, response("", reason="length", reasoning="PRIVATE-REASONING"))
    with log_context(request_id="request-length", session_id="session-length"):
        with pytest.raises(analyze.AnalysisOutputError) as caught:
            await trace_stage("analysis", analyze.analyze_papers)(STATE)
        public = error_payload(caught.value)
    assert public["code"] == "ANALYSIS_TRUNCATED" and len(calls) == 1
    failures = [r for r in capture.records if getattr(r, "fields", {}).get("error_id") == public["error_id"]]
    assert len(failures) == 1 and failures[0].message == "analysis.output.failed"
    fields = failures[0].fields
    assert fields["content_characters"] == 0 and fields["finish_reason"] == "length"
    assert fields["completion_tokens"] == fields["reasoning_tokens"] == fields["max_tokens"] == 1500
    assert fields["completion_budget_reached"] and fields["failure_kind"] == "generation_length_limit"
    assert failures[0].trace_context["stage"] == "analysis"
    assert not events(capture, "analysis.completed")
    assert "PRIVATE-REASONING" not in JsonFormatter().format(failures[0])


@pytest.mark.asyncio
@pytest.mark.parametrize("content, state", [(None, "missing"), ("", "empty"), (" \n", "whitespace")])
async def test_empty_content_states_are_distinguished_without_invented_usage(monkeypatch, capture, content, state):
    fake_client(monkeypatch, response(content, reasoning="PRIVATE-REASONING", usage=False))
    with pytest.raises(analyze.AnalysisOutputError) as caught:
        await analyze.analyze_papers(STATE)
    assert caught.value.code == "ANALYSIS_EMPTY_RESPONSE"
    fields = events(capture, "analysis.output.failed")[0].fields
    assert fields["content_state"] == state and fields["failure_kind"] == "reasoning_without_final_answer"
    assert fields["prompt_tokens"] is None and fields["completion_tokens"] is None
    assert fields["reasoning_tokens"] is None and fields["completion_budget_reached"] is None


@pytest.mark.asyncio
async def test_all_empty_input_is_reported_before_model_call(monkeypatch, capture):
    calls = fake_client(monkeypatch, response(json.dumps(VALID_REPORT)))
    with pytest.raises(analyze.AnalysisOutputError) as caught:
        await analyze.analyze_papers({"paper_insights": [{"source": "p1", "answer": " "}]})
    assert caught.value.code == "ANALYSIS_INPUT_EMPTY" and calls == []
    assert events(capture, "analysis.input.failed")[0].fields["nonempty_summaries"] == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("text, code", [('{"agreements":[', "ANALYSIS_INVALID_JSON"),
    (json.dumps({**VALID_REPORT, "agreements": "PRIVATE-INVALID-OUTPUT"}), "ANALYSIS_INVALID_SCHEMA"),
    ('{}', "ANALYSIS_INVALID_SCHEMA"), ('[]', "ANALYSIS_INVALID_SCHEMA")])
async def test_json_and_schema_errors_are_explicit_without_logging_raw_output(monkeypatch, capture, text, code):
    fake_client(monkeypatch, response(text))
    with pytest.raises(analyze.AnalysisOutputError) as caught:
        await analyze.analyze_papers(STATE)
    assert caught.value.code == code
    failure = events(capture, "analysis.output.failed")[0]
    if code == "ANALYSIS_INVALID_JSON":
        assert failure.fields["json_error_position"] is not None
    else:
        assert failure.fields["schema_errors"]
    assert "PRIVATE-INVALID-OUTPUT" not in JsonFormatter().format(failure)


@pytest.mark.asyncio
async def test_genuine_empty_analysis_is_a_valid_completed_result(monkeypatch, capture):
    empty = {"agreements": [], "contradictions": [], "methods": {}, "gaps": []}
    fake_client(monkeypatch, response('```json\n' + json.dumps(empty) + '\n```'))
    result = await analyze.analyze_papers(STATE)
    assert result["analysis_report"] == empty
    assert result["analysis_diagnostics"]["empty_analysis"]
    assert result["analysis_diagnostics"]["status"] == "completed"
    assert not events(capture, "analysis.output.failed")


@pytest.mark.asyncio
async def test_invalid_response_shape_is_traceable(monkeypatch, capture):
    fake_client(monkeypatch, SimpleNamespace(choices=[]))
    with pytest.raises(analyze.AnalysisOutputError) as caught:
        await analyze.analyze_papers(STATE)
    assert caught.value.code == "ANALYSIS_INVALID_RESPONSE"
    assert events(capture, "analysis.output.failed")[0].fields["choices_count"] == 0


@pytest.mark.asyncio
async def test_upstream_timeout_keeps_original_error_contract_and_call_context(monkeypatch, capture):
    timeout = APITimeoutError(request=httpx.Request("POST", "https://provider.test/chat/completions"))
    fake_client(monkeypatch, timeout)
    with log_context(request_id="request-timeout", session_id="session-timeout"):
        with pytest.raises(APITimeoutError) as caught:
            await analyze.analyze_papers(STATE)
        public = error_payload(caught.value)
    assert public["code"] == "UPSTREAM_TIMEOUT"
    record = events(capture, "analysis.request.failed")[0]
    assert record.fields["error_id"] == public["error_id"]
    assert record.trace_context["analysis_call_id"] and record.fields["max_tokens"] == 1500
    assert not events(capture, "analysis.response.received")


@pytest.mark.asyncio
async def test_cancellation_is_not_reported_as_model_failure(monkeypatch, capture):
    fake_client(monkeypatch, asyncio.CancelledError())
    with pytest.raises(asyncio.CancelledError):
        await analyze.analyze_papers(STATE)
    assert events(capture, "analysis.request.cancelled")
    assert not events(capture, "analysis.request.failed")
    assert current_context() == {}


@pytest.mark.asyncio
async def test_sse_analysis_failure_reports_matching_trace_id_and_no_success(monkeypatch, capture):
    fake_client(monkeypatch, response("", reason="length", reasoning="PRIVATE-REASONING"))
    class AnalysisGraph:
        async def astream(self, *args, **kwargs):
            yield ((), {**STATE, "step_count": 1, "next_agent": "analysis"})
            await trace_stage("analysis", analyze.analyze_papers)(STATE)
    monkeypatch.setattr(routes_research, "build_graph", AnalysisGraph)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=create_app(), raise_app_exceptions=False),
                                 base_url="http://test") as http:
        result = await http.post("/api/research/stream", json={"query": "test"}, headers={"X-Request-ID": "analysis-sse"})
        health = await http.get("/health")
    frames = [json.loads(line[6:]) for line in result.text.splitlines() if line.startswith("data: ")]
    error = frames[-1]
    assert error["event"] == "error" and error["code"] == "ANALYSIS_TRUNCATED"
    assert error["request_id"] == "analysis-sse"
    assert all(frame.get("stage") != "analyze" and frame["event"] != "done" for frame in frames)
    failed = events(capture, "analysis.output.failed")[0]
    assert failed.fields["error_id"] == error["error_id"] and failed.trace_context["session_id"]
    assert "PRIVATE-REASONING" not in result.text and health.status_code == 200


def test_replay_loads_original_summaries_and_objective_without_changing_history(monkeypatch, tmp_path):
    path = tmp_path / "history.db"
    saved = {"paper_insights": STATE["paper_insights"], "analysis": VALID_REPORT,
             "agent_trace": [{"next_agent": "analysis", "objective": "original objective"}]}
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE sessions(session_id TEXT, query TEXT, result_json TEXT, created_at TEXT)")
        db.execute("INSERT INTO sessions VALUES(?, ?, ?, ?)", ("saved-id", "original query", json.dumps(saved), "2026"))
    monkeypatch.setattr(diagnose_analysis, "DB_PATH", str(path))
    before = path.read_bytes()
    sid, state = diagnose_analysis.load_state("saved-id")
    assert sid == "saved-id" and state["paper_insights"] == STATE["paper_insights"]
    assert state["current_task"] == "original objective" and state["user_query"] == "original query"
    assert path.read_bytes() == before
