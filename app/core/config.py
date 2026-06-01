import os
from typing import List, Literal

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
    LLM_PROVIDER: Literal["openai", "ollama", "llamacpp"] = "openai"
    LLM_MODEL: str = "gpt-4o-mini"

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
    LLM_STOP_SEQUENCES: List[str] = ["<|im_end|>", "<|im_start|>", " assistant"]

    # Network Timeouts
    LLM_REMOTE_TIMEOUT: float = 60.0
    LLM_REMOTE_CONNECT_TIMEOUT: float = 10.0
    LLM_HEALTH_CHECK_TIMEOUT: float = 3.0

    # Hardware Allocation
    LLM_N_GPU_LAYERS: int = -1  # -1 offloads all layers to Apple Silicon / CUDA

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
    BATCH_SIZE: int = 32

    # ==========================================
    # 6. Database & Credentials Ecosystem
    # ==========================================
    DATABASE_URL: str = "postgresql://postgres:123456@localhost:5432/rag_db"
    PINECONE_INDEX_NAME: str = "semantic-search-openai"
    CLOUD: str = "aws"
    REGION: str = "us-east-1"

    # API Keys (Keep isolated at the bottom)
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    PINECONE_API_KEY: str = os.getenv("PINECONE_API_KEY", "")

    # ==========================================
    # 7. Dynamic File System Discovers
    # ==========================================
    @property
    def AVAILABLE_LOCAL_MODELS(self) -> List[str]:
        if os.path.exists(self.MODELS_DIR):
            return [f for f in os.listdir(self.MODELS_DIR) if f.endswith(".gguf")]
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
