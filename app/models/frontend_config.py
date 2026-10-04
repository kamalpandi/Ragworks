from typing import Literal

from pydantic import BaseModel


class FrontendConfig(BaseModel):
    # App Status & Routing
    APP_HOST: str
    APP_PORT: int
    DEBUG: bool
    USE_LOCAL_DB: bool

    # Provider Matrix
    LLM_PROVIDER: Literal["openai", "ollama", "llamacpp", "deepseek"]
    LOCAL_MODEL: str
    AVAILABLE_LOCAL_MODELS: list[str]
    LLM_MODEL: str
    OLLAMA_MODEL: str
    REMOTE_LLAMACPP_URL: str
    OLLAMA_BASE_URL: str

    # Context Constraints & Generation Telemetry
    LLM_TEMP: float
    LLM_MAX_TOKENS: int
    LLM_N_CTX: int
    LLM_STOP_SEQUENCES: list[str]

    # Vector Space Definitions
    EMBEDDING_MODEL: str
    EMBEDDING_DIMENSION: int
    EMBEDDING_MODEL_MAX_TOKEN: int

    # RAG Orchestration Parameters
    SYSTEM_PROMPT_FILE: str
    CHUNKING_STRATEGY: Literal["paragraph", "recursive", "semantic"]
    ENABLE_TABLE_PARSING: bool
    TOP_K: int
    RETRIEVAL_TOP_K: int
    INDEX_NAME: str
    CLOUD: str
    REGION: str
    BATCH_SIZE: int

    # Reranker
    RERANKER_ENABLED: bool
    RERANKER_PROVIDER: Literal["flashrank", "bge", "cohere"]
    RERANK_TOP_K: int

    # Rate limiting
    RATE_LIMIT_ENABLED: bool

    # Observability
    OBSERVABILITY_ENABLED: bool
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR"]
    LOG_FORMAT: Literal["json", "console"]
    OTEL_EXPORTER_TYPE: Literal["otlp", "console", "none"]
    OTEL_EXPORTER_ENDPOINT: str

    # Evaluation
    EVAL_ENABLED: bool
    EVAL_METRICS: list[str]
    EVAL_RESULTS_DIR: str
