from __future__ import annotations

import asyncio
import os
import re
import tempfile
from pathlib import Path

from backend.api.schemas.settings import EXAMPLE_API_KEYS, DeepSeekSettingsResponse
from backend.config import Settings


DEEPSEEK_KEY_LINE = re.compile(r"^\s*DEEPSEEK_API_KEY\s*=")


class DeepSeekSettingsWriteError(Exception):
    pass


class DeepSeekSettingsService:
    def __init__(self, app_settings: Settings, env_path: Path) -> None:
        self._settings = app_settings
        self._env_path = env_path
        self._write_lock = asyncio.Lock()

    def get(self) -> DeepSeekSettingsResponse:
        api_key = self._settings.deepseek_api_key.strip()
        return DeepSeekSettingsResponse(
            default_model=self._settings.default_model,
            api_key_required=self._settings.research_runner_mode == "real",
            api_key_configured=bool(api_key)
            and api_key.lower() not in EXAMPLE_API_KEYS,
        )

    async def update_api_key(self, api_key: str) -> DeepSeekSettingsResponse:
        async with self._write_lock:
            try:
                self._write_env(api_key)
            except OSError as exc:
                raise DeepSeekSettingsWriteError from exc
            self._settings.deepseek_api_key = api_key
        return self.get()

    def _write_env(self, api_key: str) -> None:
        self._env_path.parent.mkdir(parents=True, exist_ok=True)
        current = self._read_env()
        updated = _upsert_deepseek_api_key(current, api_key)
        temporary_path: str | None = None
        try:
            descriptor, temporary_path = tempfile.mkstemp(
                dir=self._env_path.parent,
                prefix=".env.",
                suffix=".tmp",
            )
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
                handle.write(updated)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_path, self._env_path)
            temporary_path = None
        finally:
            if temporary_path is not None:
                try:
                    os.unlink(temporary_path)
                except FileNotFoundError:
                    pass

    def _read_env(self) -> str:
        try:
            with self._env_path.open("r", encoding="utf-8", newline="") as handle:
                return handle.read()
        except FileNotFoundError:
            return ""


def _upsert_deepseek_api_key(current: str, api_key: str) -> str:
    replacement = f'DEEPSEEK_API_KEY="{_escape_dotenv_value(api_key)}"'
    lines = current.splitlines(keepends=True)
    updated_lines: list[str] = []
    replaced = False

    for line in lines:
        content = line.rstrip("\r\n")
        line_ending = line[len(content) :]
        if DEEPSEEK_KEY_LINE.match(content):
            if not replaced:
                updated_lines.append(replacement + line_ending)
                replaced = True
            continue
        updated_lines.append(line)

    if replaced:
        return "".join(updated_lines)

    newline = "\r\n" if "\r\n" in current else "\n"
    if current and not current.endswith(("\n", "\r")):
        current += newline
    return f"{current}{replacement}{newline}"


def _escape_dotenv_value(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')
