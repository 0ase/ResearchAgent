import asyncio

import pytest
from fastapi.testclient import TestClient

from backend.api.dependencies import get_deepseek_settings_service
from backend.config import Settings
from backend.main import create_app
from backend.services.deepseek_settings import (
    DeepSeekSettingsService,
    DeepSeekSettingsWriteError,
)


def make_settings(**overrides) -> Settings:
    values = {"deepseek_api_key": "", **overrides}
    return Settings(_env_file=None, **values)


def test_update_preserves_env_content_and_is_available_immediately(tmp_path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text(
        "# Local settings\r\nDEFAULT_MODEL=deepseek-v4-flash\r\nOTHER=value\r\n",
        encoding="utf-8",
        newline="",
    )
    settings = make_settings()
    service = DeepSeekSettingsService(settings, env_path)

    response = asyncio.run(service.update_api_key("sk-new-key"))

    content = env_path.read_text(encoding="utf-8")
    assert "# Local settings" in content
    assert "DEFAULT_MODEL=deepseek-v4-flash" in content
    assert "OTHER=value" in content
    assert 'DEEPSEEK_API_KEY="sk-new-key"' in content
    assert settings.deepseek_api_key == "sk-new-key"
    assert response.api_key_configured is True
    assert "sk-new-key" not in response.model_dump_json()
    reloaded = Settings(_env_file=env_path)
    assert reloaded.deepseek_api_key == "sk-new-key"


def test_update_replaces_duplicate_canonical_entries(tmp_path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text(
        "DEEPSEEK_API_KEY=old\nKEEP=1\nDEEPSEEK_API_KEY=duplicate\n",
        encoding="utf-8",
    )
    service = DeepSeekSettingsService(make_settings(), env_path)

    asyncio.run(service.update_api_key("sk-replacement"))

    content = env_path.read_text(encoding="utf-8")
    assert content.count("DEEPSEEK_API_KEY=") == 1
    assert "KEEP=1" in content
    assert "old" not in content
    assert "duplicate" not in content


def test_placeholder_is_reported_as_unconfigured(tmp_path) -> None:
    settings = make_settings(deepseek_api_key="sk-your-key-here")
    service = DeepSeekSettingsService(settings, tmp_path / ".env")

    assert service.get().api_key_configured is False


def test_demo_runner_does_not_require_a_key(tmp_path) -> None:
    service = DeepSeekSettingsService(
        make_settings(research_runner_mode="demo"),
        tmp_path / ".env",
    )

    assert service.get().api_key_required is False


def test_write_failure_keeps_runtime_and_file_unchanged(tmp_path, monkeypatch) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("KEEP=original\n", encoding="utf-8")
    settings = make_settings(deepseek_api_key="sk-existing")
    service = DeepSeekSettingsService(settings, env_path)

    def fail_write(_api_key: str) -> None:
        raise OSError("disk unavailable")

    monkeypatch.setattr(service, "_write_env", fail_write)

    with pytest.raises(DeepSeekSettingsWriteError):
        asyncio.run(service.update_api_key("sk-new"))
    assert settings.deepseek_api_key == "sk-existing"
    assert env_path.read_text(encoding="utf-8") == "KEEP=original\n"


def test_settings_api_never_returns_the_key(tmp_path) -> None:
    service = DeepSeekSettingsService(make_settings(), tmp_path / ".env")
    app = create_app()
    app.dependency_overrides[get_deepseek_settings_service] = lambda: service

    with TestClient(app) as client:
        initial = client.get("/api/v1/settings/deepseek")
        updated = client.put(
            "/api/v1/settings/deepseek",
            json={"api_key": "sk-api-secret"},
        )

    assert initial.status_code == 200
    assert initial.json() == {
        "provider": "deepseek",
        "default_model": "deepseek-v4-flash",
        "api_key_required": True,
        "api_key_configured": False,
    }
    assert updated.status_code == 200
    assert updated.json()["api_key_configured"] is True
    assert "sk-api-secret" not in updated.text


def test_settings_api_returns_a_safe_retryable_write_error(
    tmp_path,
    monkeypatch,
) -> None:
    service = DeepSeekSettingsService(make_settings(), tmp_path / ".env")

    def fail_write(_api_key: str) -> None:
        raise OSError("secret disk detail")

    monkeypatch.setattr(service, "_write_env", fail_write)
    app = create_app()
    app.dependency_overrides[get_deepseek_settings_service] = lambda: service

    with TestClient(app) as client:
        response = client.put(
            "/api/v1/settings/deepseek",
            json={"api_key": "sk-never-return-this"},
        )

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "DEEPSEEK_SETTINGS_WRITE_FAILED"
    assert response.json()["error"]["retryable"] is True
    assert "sk-never-return-this" not in response.text
    assert "secret disk detail" not in response.text


@pytest.mark.parametrize(
    "api_key",
    ["", "   ", "sk-your-key-here", "line-one\nline-two"],
)
def test_settings_api_rejects_invalid_keys(tmp_path, api_key: str) -> None:
    service = DeepSeekSettingsService(make_settings(), tmp_path / ".env")
    app = create_app()
    app.dependency_overrides[get_deepseek_settings_service] = lambda: service

    with TestClient(app) as client:
        response = client.put(
            "/api/v1/settings/deepseek",
            json={"api_key": api_key},
        )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    if api_key.strip():
        assert api_key not in response.text
