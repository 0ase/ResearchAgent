from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


# 用来配置模型 
class Settings(BaseSettings):
    anthropic_api_key: str = Field(default="", env="ANTHROPIC_API_KEY")
    openai_api_key: str = Field(default="", env="OPENAI_API_KEY")
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # 默认模型 轻量模型 嵌入模型
    default_model:str = Field(default="deepseek-v4-pro", description="The default model to use for the API")
    light_model:str = Field(default="deepseek-v4-flash", description="The light model to use for the API")
    dashscope_api_key: str = Field(default="", env="DASHSCOPE_API_KEY")
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

    unpaywall_email: str = Field(default="research@example.com", env="UNPAYWALL_EMAIL")
    http_proxy: str = Field(default="", env="UNPAYWALL_PROXY")

settings = Settings()