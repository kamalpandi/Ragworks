from typing import Literal, List
from pydantic import BaseModel


class FrontendConfig(BaseModel):
    # App Status & Routing
    APP_HOST: str
    APP_PORT: int
    DEBUG: bool
    USE_LOCAL_DB: bool

    # Provider Matrix
    LLM_PROVIDER: Literal["openai", "ollama", "llamacpp"]
    LOCAL_MODEL: str
    AVAILABLE_LOCAL_MODELS: List[str]
    LLM_MODEL: str
    OLLAMA_MODEL: str
    REMOTE_LLAMACPP_URL: str
    OLLAMA_BASE_URL: str

    # Context Constraints & Generation Telemetry
    LLM_TEMP: float
    LLM_MAX_TOKENS: int
    LLM_N_CTX: int
    LLM_STOP_SEQUENCES: List[str]

    # Vector Space Definitions
    EMBEDDING_MODEL: str
    EMBEDDING_DIMENSION: int
    EMBEDDING_MODEL_MAX_TOKEN: int

    # RAG Orchestration Parameters
    SYSTEM_PROMPT_FILE: str
    CHUNKING_STRATEGY: Literal["paragraph", "recursive", "semantic"]
    ENABLE_TABLE_PARSING: bool
    TOP_K: int
    INDEX_NAME: str
    CLOUD: str
    REGION: str
    BATCH_SIZE: int
