from app.components.embedders.openai_embedder import OpenAIEmbedder
from app.components.llms.factory import get_llm_provider
from app.components.rerankers.factory import get_reranker
from app.components.vector_dbs.pgvector_db import PGVectorDB
from app.components.vector_dbs.pinecone_db import PineconeDB
from app.core.config import settings
from app.core.prompt_loader import load_prompt
from app.observability.logger import get_logger
from app.services.ingestion import IngestionService
from app.services.rag_engine import RAGEngine

logger = get_logger(__name__)
USE_LOCAL_DB: bool = settings.USE_LOCAL_DB


def get_vector_db():
    return get_db()


def get_db():
    if USE_LOCAL_DB:
        logger.info("using_local_vector_db", provider="pgvector")
        return PGVectorDB()
    else:
        logger.info("using_cloud_vector_db", provider="pinecone")
        return PineconeDB()


# --- Dependency Injection ---
llm_backend = get_llm_provider()
reranker = get_reranker()


def get_ingestion_service(tenant_id: str = "default") -> IngestionService:
    return IngestionService(embedder=OpenAIEmbedder(), vector_db=get_db())


def get_rag_engine(tenant_id: str = "default") -> RAGEngine:
    system_prompt = load_prompt(settings.SYSTEM_PROMPT_FILE)
    return RAGEngine(
        vector_db=get_db(),
        embedder=OpenAIEmbedder(),
        llm=llm_backend,
        system_prompt=system_prompt,
        reranker=reranker,
    )


def get_eval_runner():
    """Lazy-load evaluation runner only when eval endpoints are hit."""
    from app.evaluation.runner import EvaluationRunner

    return EvaluationRunner(rag_engine=get_rag_engine())
