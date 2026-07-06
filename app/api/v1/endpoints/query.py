from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.components.query_translation.enricher import enrich_query
from app.core.dependencies import get_rag_engine, load_prompt
from app.models.api_requests import ChatRequest
from app.models.api_response import QueryResponse

router = APIRouter()


@router.post(
    "",
    response_model=QueryResponse,
    summary="Query a specific file in the RAG knowledge base",
)
async def query_knowledge_base(
    request: ChatRequest, request_ctx: Request, engine=Depends(get_rag_engine)
):
    """
    Search and Answer isolated to the requesting tenant.

    - **message**: Your question
    - **file_name**: Optional target file to filter search within tenant scope
    - **translation_strategy**: Optional strategy (multi_query, hyde, etc.)
    - **prompt_name**: Optional custom system prompt name
    - **custom_prompt**: Optional inline custom system prompt text (overrides prompt_name)
    - **thread_id**: Optional conversation thread for follow-up questions
    """
    if request.custom_prompt and request.custom_prompt.strip():
        system_report = request.custom_prompt.strip()
    elif request.prompt_name:
        system_report = load_prompt(request.prompt_name)
    else:
        system_report = None
    enriched_query = enrich_query(request.message, request.file_name)

    try:
        result = await engine.answer_question(
            query=enriched_query,
            file_filter=request.file_name,
            translation_strategy=request.translation_strategy,
            system_prompt=system_report,
            tenant_id=getattr(request_ctx.state, "tenant_id", "default"),
            thread_id=request.thread_id,
        )
        return result
    except RuntimeError as e:
        error_msg = str(e)
        if "Remote LLM Server returned error status 400" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error_code": "CONTEXT_WINDOW_EXCEEDED",
                    "message": "The combined length of your question and the retrieved documentation context is too large for the LLM server's current limits.",
                    "technical_details": error_msg,
                },
            )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error_code": "INTERNAL_SERVER_ERROR", "message": error_msg},
        )
