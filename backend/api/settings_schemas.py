"""Local configuration contract, separate from research request schemas."""
from pydantic import BaseModel, ConfigDict, SecretStr


class SettingsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    values: dict[str, str | int | float] = {}
    secrets: dict[str, SecretStr] = {}
    clear_secrets: list[str] = []
