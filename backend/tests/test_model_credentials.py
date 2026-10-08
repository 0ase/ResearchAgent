import json
from types import SimpleNamespace

import httpx
import pytest

from backend.agents.supervisor import supervisor
from backend.config import Settings, settings
from backend.core.errors import AppError
from backend.main import create_app


@pytest.mark.parametrize("openai_key,anthropic_key,expected", [
    ("openai-test-key", "", "openai-test-key"),
    ("", "anthropic-test-key", "anthropic-test-key"),
    ("openai-test-key", "anthropic-test-key", "openai-test-key"),
    ("  ", "anthropic-test-key", "anthropic-test-key"),
    (" openai-test-key ", "anthropic-test-key", "openai-test-key"),
    ("", " anthropic-test-key ", "anthropic-test-key"),
])
def test_selects_configured_key(openai_key, anthropic_key, expected):
    config = Settings(
        _env_file=None, OPENAI_API_KEY=openai_key, ANTHROPIC_API_KEY=anthropic_key,
    )
    assert config.llm_api_key == expected


@pytest.mark.parametrize("openai_key,anthropic_key", [("", ""), (" \t", "\n ")])
def test_missing_keys_raise_clear_configuration_error(openai_key, anthropic_key):
    config = Settings(
        _env_file=None, OPENAI_API_KEY=openai_key, ANTHROPIC_API_KEY=anthropic_key,
    )
    with pytest.raises(AppError) as captured:
        _ = config.llm_api_key
    assert captured.value.code == "MODEL_CREDENTIALS_MISSING"
    assert captured.value.status_code == 503


@pytest.mark.asyncio
@pytest.mark.parametrize("configured_field", ["openai_api_key", "anthropic_api_key"])
async def test_supervisor_works_with_either_key(monkeypatch, configured_field):
    monkeypatch.setattr(settings, "openai_api_key", "")
    monkeypatch.setattr(settings, "anthropic_api_key", "")
    monkeypatch.setattr(settings, configured_field, "test-selected-key")
    calls = []

    async def create(**kwargs):
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(
            content=json.dumps({
                "next_agent": "retrieval", "objective": "Find papers", "reason": "Need evidence",
            }),
        ))])

    def fake_client(**kwargs):
        calls.append(kwargs)
        assert kwargs["api_key"] == "test-selected-key"
        return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))

    monkeypatch.setattr("backend.agents.supervisor.AsyncOpenAI", fake_client)
    command = await supervisor({"user_query": "test query", "step_count": 0, "max_steps": 12})
    assert command.goto == "retrieval"
    assert len(calls) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("endpoint", ["/api/research/", "/api/research/stream"])
async def test_missing_keys_are_reported_through_http_and_sse(monkeypatch, endpoint):
    monkeypatch.setattr(settings, "openai_api_key", "")
    monkeypatch.setattr(settings, "anthropic_api_key", "")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=create_app(), raise_app_exceptions=False),
        base_url="http://test",
    ) as client:
        response = await client.post(endpoint, json={"query": "test query"})
    if endpoint.endswith("stream"):
        events = [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")]
        error = events[-1]
        assert error["event"] == "error"
        assert response.status_code == 200
    else:
        error = response.json()["error"]
        assert response.status_code == 503
    assert error["code"] == "MODEL_CREDENTIALS_MISSING"
    assert error["status_code"] == 503
    assert "OPENAI_API_KEY" in error["message"] and "ANTHROPIC_API_KEY" in error["message"]
    assert error["error_id"] and error["request_id"]
