from app.components.embedders.openai_embedder import OpenAIEmbedder
from app.components.llms.factory import get_llm_provider
from app.components.vector_dbs.pgvector_db import PGVectorDB
from app.components.vector_dbs.pinecone_db import PineconeDB
from app.core.config import settings
from app.core.prompt_loader import load_prompt
from app.services.ingestion import IngestionService
from app.services.rag_engine import RAGEngine

USE_LOCAL_DB: bool = settings.USE_LOCAL_DB


def get_vector_db():
    return get_db()


def get_db():
    if USE_LOCAL_DB:
        print("Using Local PGVector")
        return PGVectorDB()
    else:
        print("Using Pinecone")
        return PineconeDB()


# --- Dependency Injection ---
def get_ingestion_service() -> IngestionService:
    return IngestionService(embedder=OpenAIEmbedder(), vector_db=get_db())


llm_backend = get_llm_provider()


def get_rag_engine() -> RAGEngine:
    system_prompt = load_prompt(settings.SYSTEM_PROMPT_FILE)
    return RAGEngine(
        vector_db=get_db(),
        embedder=OpenAIEmbedder(),
        llm=llm_backend,
        system_prompt=system_prompt,
    )
