"""Generation recovery, provider compatibility and complete-output behavior."""
import json
from types import SimpleNamespace

import pytest

from backend.agents import analyze
from backend.config import Settings, settings
from backend.core.errors import error_payload
from backend.core.observability import current_context, log_context

REPORT = {"agreements": ["共同支持预测建模"], "contradictions": [],
          "methods": {"world model": [1, 3]}, "gaps": ["缺乏一致的长期评估"]}
STATE = {"user_query": "机器人世界模型", "paper_insights": [
    {"source": "p1", "answer": "机器人世界模型贡献一"},
    {"source": "p2", "answer": " "},
    {"source": "p3", "answer": "机器人世界模型贡献二"}]}


def completion(text, *, reason="stop", tokens=1200, reasoning=0):
    return SimpleNamespace(id=f"response-{reason}-{tokens}", model="deepseek-flash",
        choices=[SimpleNamespace(finish_reason=reason, message=SimpleNamespace(
            content=text, reasoning_content="thinking" if reasoning else None,
            refusal=None, tool_calls=None))],
        usage=SimpleNamespace(prompt_tokens=1000, completion_tokens=tokens, total_tokens=1000 + tokens,
                              completion_tokens_details=SimpleNamespace(reasoning_tokens=reasoning)))


def client(monkeypatch, responses):
    calls = []
    constructors = []
    async def create(**kwargs):
        calls.append(kwargs)
        return responses.pop(0)
    def construct(**kwargs):
        constructors.append(kwargs)
        return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    monkeypatch.setattr(analyze, "AsyncOpenAI", construct)
    monkeypatch.setattr(settings, "openai_api_key", "test-key")
    monkeypatch.setattr(settings, "base_url", "https://api.deepseek.com")
    monkeypatch.setattr(settings, "analysis_max_tokens", 6000)
    monkeypatch.setattr(settings, "analysis_retry_max_tokens", 8000)
    monkeypatch.setattr(settings, "analysis_max_attempts", 2)
    monkeypatch.setattr(settings, "analysis_thinking_effort", "low")
    return calls, constructors


@pytest.mark.asyncio
async def test_length_failure_recovers_with_larger_budget_and_final_answer_mode(monkeypatch):
    calls, constructors = client(monkeypatch, [completion("", reason="length", tokens=6000, reasoning=6000),
                                              completion(json.dumps(REPORT))])
    with log_context(request_id="recovery-request", session_id="recovery-session"):
        result = await analyze.analyze_papers(STATE)
    assert result["analysis_report"] == REPORT and len(constructors) == 1
    assert [call["max_tokens"] for call in calls] == [6000, 8000]
    assert [call["reasoning_effort"] for call in calls] == ["low", "none"]
    assert [call["extra_body"]["thinking"]["type"] for call in calls] == ["enabled", "disabled"]
    assert all(call["response_format"] == {"type": "json_object"} for call in calls)
    diagnostics = result["analysis_diagnostics"]
    assert diagnostics["recovered"] and diagnostics["attempts_count"] == 2
    first, second = diagnostics["attempts"]
    assert first["error_code"] == "ANALYSIS_TRUNCATED" and first["error_id"]
    assert first["analysis_call_id"] != second["analysis_call_id"]
    assert first["analysis_run_id"] == second["analysis_run_id"] == diagnostics["analysis_run_id"]
    assert diagnostics["counts"]["agreements"] == 1 and current_context() == {}


@pytest.mark.asyncio
@pytest.mark.parametrize("bad", ["", '{"agreements":[', '{}'])
async def test_empty_json_and_schema_failures_get_one_corrective_attempt(monkeypatch, bad):
    calls, _ = client(monkeypatch, [completion(bad), completion(json.dumps(REPORT))])
    result = await analyze.analyze_papers(STATE)
    assert len(calls) == 2 and result["analysis_report"] == REPORT
    assert "previous attempt failed" in calls[1]["messages"][-1]["content"].lower()
    assert "机器人世界模型贡献一" in calls[1]["messages"][1]["content"]


@pytest.mark.asyncio
async def test_recovery_is_bounded_and_keeps_final_error_trace(monkeypatch):
    calls, _ = client(monkeypatch, [completion("", reason="length", tokens=6000, reasoning=6000),
                                   completion("", reason="length", tokens=8000, reasoning=8000)])
    with log_context(request_id="bounded-request"):
        with pytest.raises(analyze.AnalysisOutputError) as caught:
            await analyze.analyze_papers(STATE)
        public = error_payload(caught.value)
    assert len(calls) == 2 and public["code"] == "ANALYSIS_TRUNCATED"
    assert public["error_id"] == caught.value._bigone_error_id
    assert caught.value.trace_context["analysis_attempt"] == 2


@pytest.mark.asyncio
async def test_complete_valid_json_at_limit_is_kept_without_extra_call(monkeypatch):
    calls, _ = client(monkeypatch, [completion(json.dumps(REPORT), reason="length", tokens=6000)])
    result = await analyze.analyze_papers(STATE)
    assert len(calls) == 1 and result["analysis_report"] == REPORT
    assert result["analysis_diagnostics"]["finish_reason"] == "length"
    assert not result["analysis_diagnostics"]["recovered"]


@pytest.mark.asyncio
async def test_content_filter_is_not_retried_in_another_mode(monkeypatch):
    calls, _ = client(monkeypatch, [completion("", reason="content_filter")])
    with pytest.raises(analyze.AnalysisOutputError) as caught:
        await analyze.analyze_papers(STATE)
    assert caught.value.code == "ANALYSIS_RESPONSE_REJECTED" and len(calls) == 1


@pytest.mark.asyncio
async def test_empty_summaries_are_omitted_without_renumbering_evidence(monkeypatch):
    calls, _ = client(monkeypatch, [completion(json.dumps(REPORT))])
    result = await analyze.analyze_papers(STATE)
    prompt = calls[0]["messages"][1]["content"]
    assert "Paper 1 [Source p1]" in prompt and "Paper 3 [Source p3]" in prompt
    assert "Paper 2" not in prompt
    assert result["analysis_diagnostics"]["sent_summaries"] == 2
    assert result["analysis_diagnostics"]["empty_summaries"] == 1


@pytest.mark.asyncio
async def test_other_compatible_providers_do_not_receive_deepseek_controls(monkeypatch):
    calls, _ = client(monkeypatch, [completion(json.dumps(REPORT))])
    monkeypatch.setattr(settings, "base_url", "https://provider.test/v1")
    result = await analyze.analyze_papers(STATE)
    assert "extra_body" not in calls[0] and "reasoning_effort" not in calls[0]
    assert "response_format" not in calls[0]
    assert result["analysis_diagnostics"]["thinking_setting"] == "provider_default"


def test_recovery_configuration_bounds():
    with pytest.raises(ValueError):
        Settings(_env_file=None, analysis_max_tokens=9000, analysis_retry_max_tokens=8000)
    with pytest.raises(ValueError):
        Settings(_env_file=None, analysis_max_attempts=0)
