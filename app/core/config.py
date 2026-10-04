import os
from typing import Literal

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # ==========================================
    # 1. Core Application Metadata
    # ==========================================
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    APP_WORKERS: int = 1
    APP_RELOAD: bool = False
    DEBUG: bool = False
    USE_LOCAL_DB: bool = True

    # ==========================================
    # 2. Dynamic Model Providers & Engines
    # ==========================================
    LLM_PROVIDER: Literal["openai", "ollama", "llamacpp", "deepseek"] = "openai"
    LLM_MODEL: str = "gpt-4o-mini"

    # DeepSeek Specifics
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com/v1"
    DEEPSEEK_MODEL: str = "deepseek-chat"

    # Ollama Specifics
    OLLAMA_MODEL: str = "llama3"
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    # Llama.cpp Remote / Local Specifics
    REMOTE_LLAMACPP_URL: str = "http://192.168.0.225:8080"
    MODELS_DIR: str = "models"

    # ==========================================
    # 3. Guardrails & Token Constraints
    # ==========================================
    LLM_TEMP: float = 0
    LLM_MAX_TOKENS: int = 2000
    LLM_N_CTX: int = 4000
    LLM_TOP_P: float = 0.9
    LLM_STOP_SEQUENCES: list[str] = ["<|im_end|>", "<|im_start|>", " assistant"]

    # Network Timeouts
    LLM_REMOTE_TIMEOUT: float = 60.0
    LLM_REMOTE_CONNECT_TIMEOUT: float = 10.0
    LLM_HEALTH_CHECK_TIMEOUT: float = 3.0

    # Hardware Allocation
    LLM_N_GPU_LAYERS: int = -1  # -1 offloads all layers to Apple Silicon / CUDA

    # LLM Concurrency (local providers)
    LLM_QUEUE_TIMEOUT_SECONDS: float = 120.0

    # Conversation Memory
    CONVERSATION_HISTORY_LENGTH: int = 10

    # ==========================================
    # 4. Embeddings & Vector Space Data
    # ==========================================
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSION: int = 512
    EMBEDDING_MODEL_MAX_TOKEN: int = 8000

    # ==========================================
    # 5. Pipeline RAG Orchestration
    # ==========================================
    SYSTEM_PROMPT_FILE: str = "default"
    CHUNKING_STRATEGY: Literal["paragraph", "recursive", "semantic"] = "recursive"
    ENABLE_TABLE_PARSING: bool = True
    TOP_K: int = 10
    RETRIEVAL_TOP_K: int = 10
    BATCH_SIZE: int = 32
    MAX_UPLOAD_SIZE_MB: int = 50

    # ==========================================
    # 5b. Reranker
    # ==========================================
    RERANKER_ENABLED: bool = True
    RERANKER_PROVIDER: Literal["flashrank", "bge", "cohere"] = "flashrank"
    RERANK_TOP_K: int = 3
    FLASHRANK_MODEL: str = "ms-marco-MiniLM-L-12-v2"
    BGE_RERANKER_MODEL: str = "BAAI/bge-reranker-v2-m3"

    # ==========================================
    # 5c. Observability & Tracing
    # ==========================================
    OBSERVABILITY_ENABLED: bool = True
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    LOG_FORMAT: Literal["json", "console"] = "console"
    OTEL_EXPORTER_TYPE: Literal["otlp", "console", "none"] = "console"
    OTEL_EXPORTER_ENDPOINT: str = "http://localhost:4317"

    # ==========================================
    # 5d. Evaluation
    # ==========================================
    EVAL_ENABLED: bool = True
    EVAL_METRICS: list[str] = [
        "context_precision",
        "context_recall",
        "faithfulness",
        "answer_relevancy",
    ]
    EVAL_RESULTS_DIR: str = "eval_results"

    # ==========================================
    # 6. Database & Credentials Ecosystem
    # ==========================================
    DATABASE_URL: str = "postgresql://postgres:123456@localhost:5432/rag_db"
    PINECONE_INDEX_NAME: str = "semantic-search-openai"
    CLOUD: str = "aws"
    REGION: str = "us-east-1"

    # Connection Pooling
    DB_POOL_MIN_SIZE: int = 2
    DB_POOL_MAX_SIZE: int = 10
    DB_POOL_TIMEOUT: float = 30.0

    # ==========================================
    # 8. Authentication & Security
    # ==========================================
    AUTH_ENABLED: bool = True
    AUTH_EXEMPT_PATHS: str = "/metrics,/docs,/openapi.json,/health,/login,/favicon.ico"
    ADMIN_API_KEY: str = os.getenv("ADMIN_API_KEY", "admin-change-me")
    DEV_API_KEY: str = os.getenv("DEV_API_KEY", "")

    # Frontend server-side sessions & CSRF
    SESSION_COOKIE_NAME: str = "rag_session"
    SESSION_TTL_SECONDS: int = 28800  # 8 hours
    SESSION_COOKIE_SECURE: bool = False  # set True behind HTTPS
    CSRF_HEADER_NAME: str = "X-CSRF-Token"
    PRE_SESSION_TTL_SECONDS: int = 1800  # 30 minutes (login page)

    # ==========================================
    # 9. Rate Limiting
    # ==========================================
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_QUERIES_PER_MINUTE: int = 60
    RATE_LIMIT_INGEST_PER_MINUTE: int = 10
    RATE_LIMIT_BURST_SIZE: int = 5

    # CORS
    CORS_ALLOWED_ORIGINS: str = os.getenv("CORS_ALLOWED_ORIGINS", "*")

    # API Keys (Keep isolated at the bottom)
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    PINECONE_API_KEY: str = os.getenv("PINECONE_API_KEY", "")

    # ==========================================
    # 7. Dynamic File System Discovers
    # ==========================================
    @property
    def AVAILABLE_LOCAL_MODELS(self) -> list[str]:
        try:
            if os.path.exists(self.MODELS_DIR):
                return [f for f in os.listdir(self.MODELS_DIR) if f.endswith(".gguf")]
        except (FileNotFoundError, NotADirectoryError):
            pass
        return []

    # Local fallback initializer
    LOCAL_MODEL: str = os.getenv(
        "LOCAL_MODEL",
        next(
            (f"models/{f}" for f in os.listdir("models") if f.endswith(".gguf")),
            "No local model found",
        )
        if os.path.exists("models")
        else "No local model found",
    )


settings = Settings()
