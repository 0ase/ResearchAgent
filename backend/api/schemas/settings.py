from typing import Literal

from pydantic import BaseModel, Field, field_validator


EXAMPLE_API_KEYS = {
    "sk-your-key-here",
    "your-deepseek-api-key",
}


class DeepSeekSettingsResponse(BaseModel):
    provider: Literal["deepseek"] = "deepseek"
    default_model: str
    api_key_required: bool
    api_key_configured: bool


class UpdateDeepSeekSettingsRequest(BaseModel):
    api_key: str = Field(min_length=1, max_length=1000)

    @field_validator("api_key")
    @classmethod
    def validate_api_key(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized or normalized.lower() in EXAMPLE_API_KEYS:
            raise ValueError("a DeepSeek API key is required")
        if any(character in normalized for character in ("\r", "\n", "\x00")):
            raise ValueError("API key must be a single line")
        return normalized
