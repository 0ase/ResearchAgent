from pathlib import Path
from typing import Annotated, Literal

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ENV_PATH = PROJECT_ROOT / ".env"


# 用来配置模型 
class Settings(BaseSettings):
    environment: Literal["development", "test", "production"] = Field(
        default="development",
        validation_alias=AliasChoices("ENVIRONMENT", "environment"),
    )
    research_runner_mode: Literal["real", "demo"] = Field(
        default="real",
        validation_alias=AliasChoices("RESEARCH_RUNNER_MODE", "research_runner_mode"),
    )
    demo_delay_seconds: float = Field(
        default=0.0,
        ge=0,
        validation_alias=AliasChoices("DEMO_DELAY_SECONDS", "demo_delay_seconds"),
    )
    demo_instance_id: str = Field(
        default="",
        validation_alias=AliasChoices("DEMO_INSTANCE_ID", "demo_instance_id"),
    )
    deepseek_api_key: str = Field(
        default="",
        validation_alias=AliasChoices(
            "DEEPSEEK_API_KEY",
            "ANTHROPIC_API_KEY",
            "deepseek_api_key",
            "anthropic_api_key",
        ),
    )
    openai_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("OPENAI_API_KEY", "openai_api_key"),
    )
    model_config = SettingsConfigDict(
        env_file=PROJECT_ENV_PATH,
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    api_version: str = Field(
        default="v1",
        validation_alias=AliasChoices("API_VERSION", "api_version"),
    )
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://127.0.0.1:3000"],
        validation_alias=AliasChoices("CORS_ORIGINS", "cors_origins"),
    )
    database_path: str = Field(
        default="data/research.db",
        validation_alias=AliasChoices("DATABASE_PATH", "database_path"),
    )
    event_keepalive_seconds: int = Field(
        default=15,
        ge=1,
        validation_alias=AliasChoices(
            "EVENT_KEEPALIVE_SECONDS",
            "event_keepalive_seconds",
        ),
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> list[str]:
        if value is None:
            return ["http://localhost:3000", "http://127.0.0.1:3000"]
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        if isinstance(value, (list, tuple)):
            return [str(origin).strip() for origin in value if str(origin).strip()]
        raise ValueError("CORS_ORIGINS must be a comma-separated string or list")

    # 默认模型 轻量模型 嵌入模型
    default_model:str = Field(default="deepseek-v4-flash", description="The default model to use for the API")
    light_model:str = Field(default="deepseek-v4-flash", description="The light model to use for the API")
    dashscope_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("DASHSCOPE_API_KEY", "dashscope_api_key"),
    )
    dashscope_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    base_url: str = "https://api.deepseek.com"

    # 最大搜索次数 返回的最小论文数量 最大论文数量
    max_search_rounds: int = Field(default=3, ge=1, le=5)
    min_paper_default: int = Field(default=5, ge=1)
    max_paper_default: int = Field(default=20, ge=1)
    search_timeout_seconds: int = Field(default=30, ge=1)

    # 分块大小 分块重叠 检索 top k
    chunk_size: int = Field(default=512, ge=64)
    chunk_overlap: int = Field(default=128, ge=0)
    retrieval_top_k: int = Field(default=10, ge=1)

    # 沙盒超时时间 沙盒最大重试次数
    sandbox_timeout_seconds: int = Field(default=30)
    sandbox_max_retries: int = Field(default=2)

    # 数据库url 数据库持久化目录 论文缓存目录 图表持久化目录 arxiv 速率限制
    database_url: str = Field(default="sqlite:///data/research.db")
    chroma_persist_dir: str = Field(default="data/chroma_db", description="The directory to persist the ChromaDB database")
    paper_cache_dir: str = Field(default="data/paper_cache", description="The directory to persist the paper cache")
    figures_dir:str = Field(default="data/figures", description="The directory to persist the figures")
    arxiv_rate_limit: float = Field(default=0.33, ge=0.1)

    unpaywall_email: str = Field(
        default="research@example.com",
        validation_alias=AliasChoices("UNPAYWALL_EMAIL", "unpaywall_email"),
    )
    http_proxy: str = Field(
        default="",
        validation_alias=AliasChoices("UNPAYWALL_PROXY", "http_proxy"),
    )

settings = Settings()
