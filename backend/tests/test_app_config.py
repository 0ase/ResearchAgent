from fastapi.testclient import TestClient

from backend.config import Settings
from backend.main import create_app


def test_default_settings_allow_next_dev_server() -> None:
    settings = Settings(_env_file=None)

    assert settings.cors_origins == [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    assert settings.default_model == "deepseek-v4-flash"
    assert settings.light_model == "deepseek-v4-flash"


def test_deepseek_key_prefers_canonical_name_and_accepts_legacy_alias(
    monkeypatch,
) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "legacy-key")
    settings = Settings(_env_file=None)
    assert settings.deepseek_api_key == "legacy-key"

    monkeypatch.setenv("DEEPSEEK_API_KEY", "canonical-key")
    settings = Settings(_env_file=None)
    assert settings.deepseek_api_key == "canonical-key"


def test_cors_origins_parse_comma_separated_environment(monkeypatch) -> None:
    monkeypatch.setenv(
        "CORS_ORIGINS",
        "http://localhost:3000, https://research.example.com ,",
    )

    settings = Settings(_env_file=None)

    assert settings.cors_origins == [
        "http://localhost:3000",
        "https://research.example.com",
    ]


def test_health_exposes_status_and_api_version() -> None:
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "api_version": "v1",
        "runner_mode": "real",
        "demo_instance_id": "",
    }


def test_unknown_errors_use_safe_error_envelope() -> None:
    app = create_app()

    @app.get("/test/boom")
    async def boom() -> None:
        raise RuntimeError("secret traceback detail")

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/test/boom")

    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "INTERNAL_ERROR"
    assert body["error"]["message"] == "服务器内部错误"
    assert "secret traceback detail" not in response.text
