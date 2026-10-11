import json

import httpx
import pytest

from backend.config import Settings
from backend.main import create_app
from backend.services import settings_store as store


@pytest.fixture
def local_env(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text("# keep this comment\nOPENAI_API_KEY='old-private-key'\nDEFAULT_MODEL='local-model'\nOTHER_VALUE=keep\n", encoding="utf-8")
    monkeypatch.setattr(store, "ENV_PATH", env)
    monkeypatch.setattr(store, "PROJECT_ROOT", tmp_path)
    monkeypatch.chdir(tmp_path)
    for name in Settings.model_fields:
        env_name = store._env_name(name)
        for key in list(store.os.environ):
            if key.upper() == env_name:
                monkeypatch.delenv(key)
    # Always explicit test values; never use real keys or real dotenv files.
    monkeypatch.setattr(store, "settings", Settings(_env_file=env))
    return env


async def request(method, *, client_ip="127.0.0.1", host="127.0.0.1:3000", headers=None, data=None):
    transport = httpx.ASGITransport(app=create_app(), client=(client_ip, 1234))
    async with httpx.AsyncClient(transport=transport, base_url=f"http://{host}") as client:
        return await client.request(method, "/api/settings", headers=headers, json=data)


HEADERS = {"Origin": "http://127.0.0.1:5173", "X-B1GONE-Config": "local"}


@pytest.mark.asyncio
async def test_snapshot_and_save_keep_secrets_private_and_runtime_unchanged(local_env):
    response = await request("GET")
    assert response.status_code == 200
    assert "old-private-key" not in response.text
    assert response.json()["secrets"]["openai_api_key"]["configured"]
    response = await request("PUT", headers=HEADERS, data={"values": {"default_model": "next-model"}, "secrets": {"openai_api_key": "new-private-key"}})
    assert response.status_code == 200
    assert "new-private-key" not in response.text
    assert response.json()["restart_required"]
    assert store.settings.default_model == "local-model"
    assert store.settings.openai_api_key == "old-private-key"
    text = local_env.read_text(encoding="utf-8")
    assert "# keep this comment" in text and "OTHER_VALUE=keep" in text
    assert Settings(_env_file=local_env).openai_api_key == "new-private-key"


@pytest.mark.asyncio
async def test_empty_secret_preserved_and_explicit_clear(local_env):
    response = await request("PUT", headers=HEADERS, data={"secrets": {"openai_api_key": " "}})
    assert response.json()["changed_fields"] == []
    assert "old-private-key" in local_env.read_text()
    response = await request("PUT", headers=HEADERS, data={"clear_secrets": ["openai_api_key"]})
    assert response.status_code == 200
    assert not response.json()["secrets"]["openai_api_key"]["saved"]


@pytest.mark.asyncio
@pytest.mark.parametrize("data", [
    {"values": {"min_candidate_papers": 100, "max_candidate_papers": 80}},
    {"values": {"screening_min_score": 50, "screening_supplement_min_score": 60}},
    {"values": {"analysis_max_tokens": 10000, "analysis_retry_max_tokens": 8000}},
    {"values": {"database_url": "elsewhere"}},
    {"values": {"base_url": "https://user:password@example.com"}},
    {"values": {"base_url": "https://bad hostname.example"}},
    {"values": {"default_model": "bad\nINJECTED=value"}},
    {"secrets": {"openai_api_key": "${OTHER_SECRET}"}},
    {"secrets": {"openai_api_key": "private"}, "clear_secrets": ["openai_api_key"]},
])
async def test_invalid_update_does_not_write(local_env, data):
    before = local_env.read_bytes()
    response = await request("PUT", headers=HEADERS, data=data)
    assert response.status_code == 422
    assert local_env.read_bytes() == before
    assert "old-private-key" not in response.text


@pytest.mark.asyncio
async def test_environment_override_and_duplicate_keys(local_env, monkeypatch):
    monkeypatch.setenv("DEFAULT_MODEL", "system-model")
    local_env.write_text(local_env.read_text() + "default_model=last-model\n")
    response = await request("PUT", headers=HEADERS, data={"values": {"default_model": "saved-model"}})
    snapshot = response.json()
    assert snapshot["values"]["default_model"] == "saved-model"
    assert "default_model" in snapshot["overridden_fields"]
    assert Settings(_env_file=local_env).default_model == "system-model"
    assert local_env.read_text().lower().count("default_model=") == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("kwargs", [
    {"client_ip": "192.168.1.5"},
    {"host": "attacker.example"},
    {"headers": {"Origin": "https://attacker.example", "X-B1GONE-Config": "local"}},
    {"headers": {"X-B1GONE-Config": "local"}},
    {"headers": {"Origin": "http://localhost:5173"}},
    {"headers": {"Origin": "http://[broken", "X-B1GONE-Config": "local"}},
])
async def test_settings_reject_untrusted_requests(local_env, kwargs):
    before = local_env.read_bytes()
    response = await request("PUT", data={"values": {"default_model": "bad"}}, **kwargs)
    assert response.status_code == 403
    assert local_env.read_bytes() == before


@pytest.mark.asyncio
async def test_secret_with_quotes_backslash_roundtrips(local_env):
    key = "private'quoted\\path#suffix"
    response = await request("PUT", headers=HEADERS, data={"secrets": {"openai_api_key": key}})
    assert response.status_code == 200
    assert key not in json.dumps(response.json())
    assert Settings(_env_file=local_env).openai_api_key == key
