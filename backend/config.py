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
    # 广泛检索后按候选数量和证据缺口补检，默认最多五轮。
    max_search_rounds: int = Field(default=5, ge=1, le=6)
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
    vector_store_timeout_seconds: int = Field(default=60, ge=1, le=600)
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

    search_results_per_source: int = Field(default=20, ge=3, le=20)
    min_candidate_papers: int = Field(default=80, ge=80, le=100)
    max_candidate_papers: int = Field(default=100, ge=80, le=100)
    screening_min_score: float = Field(default=70, ge=0, le=100)
    screening_supplement_min_score: float = Field(default=65, ge=0, le=100)
    screening_batch_size: int = Field(default=5, ge=1, le=15)
    screening_max_tokens: int = Field(default=6000, ge=2000, le=16000)
    venue_quality_path: str = ""
    analysis_max_tokens: int = Field(default=6000, ge=1500, le=16000)
    analysis_retry_max_tokens: int = Field(default=8000, ge=1500, le=16000)
    analysis_max_attempts: int = Field(default=2, ge=1, le=3)
    analysis_thinking_effort: str = Field(default="low", pattern="^(none|low|high|max)$")
    # 评审轮数 / 写作上限：防止 Critic 反复打回导致综述无限重生成
    max_critique_rounds: int = Field(default=1, ge=1, le=3)
    writer_max_tokens: int = Field(default=16000, ge=1000, le=16000)
    writer_min_characters: int = Field(default=3000, ge=1000, le=20000)
    writer_continuation_tokens: int = Field(default=3000, ge=500, le=8000)
    read_concurrency: int = Field(default=5, ge=1, le=10)

    log_level: str = Field(default="INFO", pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    log_dir: str = "logs"
    log_max_bytes: int = Field(default=10 * 1024 * 1024, ge=1024)
    log_backup_count: int = Field(default=5, ge=1, le=100)

    @property
    def llm_api_key(self) -> str:
        """Use either configured key for the existing OpenAI-compatible endpoint."""
        key = self.openai_api_key.strip() or self.anthropic_api_key.strip()
        if not key:
            from backend.core.errors import AppError

            raise AppError(
                "MODEL_CREDENTIALS_MISSING",
                "未配置模型 API 密钥，请设置 OPENAI_API_KEY 或 ANTHROPIC_API_KEY。",
                503,
            )
        return key

    @model_validator(mode="after")
    def validate_chunk_window(self):
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("CHUNK_OVERLAP must be smaller than CHUNK_SIZE")
        if self.min_candidate_papers > self.max_candidate_papers:
            raise ValueError("MIN_CANDIDATE_PAPERS must not exceed MAX_CANDIDATE_PAPERS")
        if self.screening_supplement_min_score > self.screening_min_score:
            raise ValueError("SCREENING_SUPPLEMENT_MIN_SCORE must not exceed SCREENING_MIN_SCORE")
        if self.analysis_retry_max_tokens < self.analysis_max_tokens:
            raise ValueError("ANALYSIS_RETRY_MAX_TOKENS must not be smaller than ANALYSIS_MAX_TOKENS")
        return self

settings = Settings()
