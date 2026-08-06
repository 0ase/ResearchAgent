from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, model_validator


# 用来配置模型 
class Settings(BaseSettings):
    anthropic_api_key: str = Field(default="", validation_alias="ANTHROPIC_API_KEY")
    openai_api_key: str = Field(default="", validation_alias="OPENAI_API_KEY")
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # 默认模型 轻量模型 嵌入模型
    default_model:str = Field(default="deepseek-v4-pro", description="The default model to use for the API")
    light_model:str = Field(default="deepseek-chat", description="The light model to use for the API")
    dashscope_api_key: str = Field(default="", validation_alias="DASHSCOPE_API_KEY")
    dashscope_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    embedding_model: str = Field(
        default="text-embedding-v4",
        validation_alias="EMBEDDING_MODEL",
    )
    base_url: str = "https://api.deepseek.com"

    # 最大搜索次数 返回的最小论文数量 最大论文数量
    # 两轮表示“一轮广泛检索 + 最多一轮缺口补充检索”。
    max_search_rounds: int = Field(default=2, ge=1, le=3)
    min_paper_default: int = Field(default=5, ge=1)
    max_paper_default: int = Field(default=20, ge=1)
    search_timeout_seconds: int = Field(default=30, ge=1)

    # 分块大小 分块重叠 检索 top k
    chunk_size: int = Field(default=512, ge=64)
    chunk_overlap: int = Field(default=128, ge=0)
    retrieval_top_k: int = Field(default=6, ge=1, le=20)

    # 沙盒超时时间 沙盒最大重试次数
    sandbox_timeout_seconds: int = Field(default=30)
    sandbox_max_retries: int = Field(default=2)

    # 数据库url 数据库持久化目录 论文缓存目录 图表持久化目录 arxiv 速率限制
    database_url: str = Field(default="sqlite:///data/research.db")
    chroma_persist_dir: str = Field(default="data/chroma_db", description="The directory to persist the ChromaDB database")
    paper_cache_dir: str = Field(default="data/paper_cache", description="The directory to persist the paper cache")
    figures_dir:str = Field(default="data/figures", description="The directory to persist the figures")
    arxiv_rate_limit: float = Field(default=0.33, ge=0.1)

    unpaywall_email: str = Field(default="research@example.com", validation_alias="UNPAYWALL_EMAIL")
    http_proxy: str = Field(default="", validation_alias="UNPAYWALL_PROXY")
    semantic_scholar_api_key: str = Field(
        default="",
        validation_alias="SEMANTIC_SCHOLAR_API_KEY",
    )
    pubmed_api_key: str = Field(default="", validation_alias="PUBMED_API_KEY")
    pubmed_email: str = Field(default="", validation_alias="PUBMED_EMAIL")
    crossref_email: str = Field(default="", validation_alias="CROSSREF_EMAIL")

    search_results_per_source: int = Field(default=6, ge=3, le=20,)
    max_candidate_papers: int = Field(default=40, ge=10, le=100,)
    max_critique_rounds: int = Field(default=2, ge=1, le=3)
    writer_max_tokens: int = Field(default=8000, ge=1000, le=16000)
    writer_min_characters: int = Field(default=5000, ge=1000, le=20000)
    writer_continuation_tokens: int = Field(default=3000, ge=500, le=8000)
    read_concurrency: int = Field(default=5, ge=1, le=10)

    @model_validator(mode="after")
    def validate_chunk_window(self):
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("CHUNK_OVERLAP must be smaller than CHUNK_SIZE")
        return self

settings = Settings()
