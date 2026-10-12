"""Edit only explicitly supported dotenv fields; running settings stay unchanged."""
from io import StringIO
import os
from pathlib import Path
import tempfile
from threading import RLock
from urllib.parse import urlsplit

from dotenv.parser import parse_stream
from pydantic import ValidationError

from backend.config import Settings, settings
from backend.core.errors import AppError

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = PROJECT_ROOT / ".env"
_lock = RLock()

# These names are the Settings field names, never arbitrary environment keys.
VALUE_FIELDS = (
    "base_url", "default_model", "light_model", "dashscope_base_url", "embedding_model",
    "unpaywall_email", "pubmed_email", "crossref_email", "max_search_rounds",
    "min_candidate_papers", "max_candidate_papers", "screening_min_score",
    "screening_supplement_min_score", "screening_batch_size", "screening_max_tokens",
    "analysis_max_tokens", "analysis_retry_max_tokens", "analysis_max_attempts",
    "writer_max_tokens", "read_concurrency",
)
SECRET_FIELDS = (
    "openai_api_key", "anthropic_api_key", "dashscope_api_key",
    "semantic_scholar_api_key", "pubmed_api_key",
)


def _env_name(field: str) -> str:
    return str(Settings.model_fields[field].validation_alias or field).upper()


def _read_env_document():
    text = ENV_PATH.read_text(encoding="utf-8-sig") if ENV_PATH.exists() else ""
    bindings = list(parse_stream(StringIO(text)))
    if any(binding.error for binding in bindings):
        raise AppError("SETTINGS_FILE_INVALID", "配置文件存在格式错误，请先在本机检查 .env。", 422)
    values = {binding.key.upper(): binding.value or "" for binding in bindings if binding.key}
    return bindings, values


def _field_values(env: dict[str, str]) -> dict:
    return {name: env[_env_name(name)] for name in Settings.model_fields if _env_name(name) in env}


def _validate(values: dict) -> Settings:
    # Pass every field explicitly, so BaseSettings cannot silently replace the
    # proposed file values with process environment values during validation.
    merged = {name: field.default for name, field in Settings.model_fields.items()}
    merged.update(values)
    try:
        result = Settings(_env_file=None, **{str(Settings.model_fields[name].validation_alias or name): value for name, value in merged.items()})
        for name in ("base_url", "dashscope_base_url"):
            url = urlsplit(getattr(result, name))
            if url.scheme not in {"http", "https"} or not url.hostname or any(char.isspace() for char in getattr(result, name)) or url.username or url.password or url.query or url.fragment:
                raise ValueError("endpoint")
        for name in ("default_model", "light_model", "embedding_model"):
            if not getattr(result, name).strip():
                raise ValueError("model")
        if any("\n" in str(value) or "\r" in str(value) or "\x00" in str(value) for value in merged.values()):
            raise ValueError("multiline")
        return result
    except (ValidationError, ValueError):
        # Never include Pydantic's input/ctx or a chained secret-bearing error.
        raise AppError("SETTINGS_INVALID", "配置值不合法：请检查数值范围、阈值顺序、模型名称及 API 地址。", 422) from None


def _prospective(env: dict[str, str]):
    file_settings = _validate(_field_values(env))
    process_env = {key.upper(): value for key, value in os.environ.items()}
    overrides = _field_values(process_env)
    effective = _validate({**file_settings.model_dump(), **overrides})
    return file_settings, effective, overrides


def get_settings_snapshot() -> dict:
    with _lock:
        _, env = _read_env_document()
        file_settings, effective, overrides = _prospective(env)
        visible = (*VALUE_FIELDS, *SECRET_FIELDS)
        pending = [name for name in visible if getattr(settings, name) != getattr(effective, name)]
        return {
            "values": {name: getattr(file_settings, name) for name in VALUE_FIELDS},
            "effective_values": {name: getattr(settings, name) for name in VALUE_FIELDS},
            "secrets": {name: {
                "configured": bool(getattr(settings, name).strip()),
                "saved": bool(getattr(file_settings, name).strip()),
                "overridden": name in overrides,
                "pending": name in pending,
            } for name in SECRET_FIELDS},
            "overridden_fields": [name for name in visible if name in overrides],
            "pending_fields": pending,
            "restart_required": bool(pending),
            "writable": Path.cwd().resolve() == PROJECT_ROOT.resolve(),
            "runtime": {
                "config_file": str(ENV_PATH),
                "session_database": str(PROJECT_ROOT / "data" / "research.db"),
                "vector_directory": settings.chroma_persist_dir,
                "paper_cache_directory": settings.paper_cache_dir,
                "log_directory": settings.log_dir,
            },
        }


def _render_env_update(bindings, changes: dict[str, str]) -> str:
    emitted = set()
    chunks = []
    for binding in bindings:
        key = binding.key.upper() if binding.key else None
        if key not in changes:
            chunks.append(binding.original.string)
        elif key not in emitted:
            chunks.append(_env_line(key, changes[key]))
            emitted.add(key)
    if chunks and not chunks[-1].endswith("\n"):
        chunks.append("\n")
    chunks.extend(_env_line(key, value) for key, value in changes.items() if key not in emitted)
    return "".join(chunks)


def _env_line(key: str, value: str) -> str:
    # Single quotes preserve #, spaces and backslashes. Dollar expansion is
    # already part of existing Settings loading; reject interpolation below.
    escaped = value.replace("\\", "\\\\").replace("'", "\\'")
    return f"{key}='{escaped}'\n"


def save_settings_update(update) -> dict:
    if Path.cwd().resolve() != PROJECT_ROOT.resolve():
        raise AppError("SETTINGS_WORKDIR_INVALID", "请从项目根目录使用 scripts/start_backend.ps1 启动后端后再保存配置。", 409)
    if set(update.values) - set(VALUE_FIELDS) or set(update.secrets) - set(SECRET_FIELDS) or set(update.clear_secrets) - set(SECRET_FIELDS):
        raise AppError("SETTINGS_FIELD_NOT_ALLOWED", "请求包含不允许编辑的配置字段。", 422)
    if set(update.secrets) & set(update.clear_secrets):
        raise AppError("SETTINGS_CONFLICT", "同一密钥不能同时设置和清除。", 422)
    changes = {_env_name(name): str(value) for name, value in update.values.items()}
    changes.update({_env_name(name): value.get_secret_value().strip() for name, value in update.secrets.items() if value.get_secret_value().strip()})
    changes.update({_env_name(name): "" for name in update.clear_secrets})
    if any("${" in value for value in changes.values()):
        raise AppError("SETTINGS_INVALID", "配置输入不支持环境变量插值，请填写实际值。", 422)
    with _lock:
        bindings, env = _read_env_document()
        _prospective({**env, **changes})
        changed = [key for key, value in changes.items() if env.get(key) != value]
        if changed:
            rendered = _render_env_update(bindings, {key: changes[key] for key in changed})
            temp_path = None
            try:
                with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=ENV_PATH.parent, prefix=".env-write-", delete=False) as output:
                    temp_path = Path(output.name)
                    output.write(rendered)
                    output.flush()
                    os.fsync(output.fileno())
                os.replace(temp_path, ENV_PATH)
            finally:
                if temp_path is not None:
                    temp_path.unlink(missing_ok=True)
        snapshot = get_settings_snapshot()
        snapshot["changed_fields"] = [name for name in (*VALUE_FIELDS, *SECRET_FIELDS) if _env_name(name) in changed]
        return snapshot
