from typing import Optional

import markdown
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse

from app.components.query_translation.enricher import enrich_query
from app.core.dependencies import get_rag_engine, get_vector_db
from app.core.prompt_loader import get_available_prompts, load_prompt
from app.services.conversation_service import list_threads
from app.ui import templates

router = APIRouter()


@router.get("/query", response_class=HTMLResponse)
async def query_page(request: Request, vector_db=Depends(get_vector_db)):
    """Renders the main Chat/Query layout shell with dynamic prompts"""
    available_prompts = get_available_prompts(category="system")
    tenant_id = getattr(request.state, "tenant_id", "default")
    available_files = await vector_db.get_distinct_sources(tenant_id=tenant_id)
    threads = await list_threads(tenant_id=tenant_id)

    return templates.TemplateResponse(
        request=request,
        name="pages/query.html",
        context={
            "available_prompts": available_prompts,
            "available_files": available_files,
            "threads": threads,
        },
    )


@router.post("/ui/query/chat", response_class=HTMLResponse)
async def ui_chat(
    request: Request,
    message: str = Form(...),
    file_name: Optional[str] = Form(None),
    translation_strategy: Optional[str] = Form(None),
    prompt_name: Optional[str] = Form(None),
    thread_id: Optional[str] = Form(None),
    engine=Depends(get_rag_engine),
    custom_prompt: Optional[str] = Form(None),
):
    # 1. HTML Forms send empty strings instead of None, so we clean them up
    strategy = (
        translation_strategy
        if translation_strategy and translation_strategy.strip()
        else None
    )
    # --- New System Prompt Logic ---
    # 1. Custom text overrides everything else
    if custom_prompt and custom_prompt.strip():
        system_report = custom_prompt.strip()
    # 2. If no custom text, load the selected template file
    elif prompt_name and prompt_name.strip():
        system_report = load_prompt(prompt_name.strip())
    # 3. Fallback to None (RAG engine will use its default)
    else:
        system_report = None

    resolved_file = file_name.strip() if file_name and file_name.strip() else None

    enriched_query = enrich_query(message, file_name or "")

    try:
        result = await engine.answer_question(
            query=enriched_query,
            file_filter=resolved_file,
            translation_strategy=strategy,
            system_prompt=system_report,
            tenant_id=getattr(request.state, "tenant_id", "default"),
            thread_id=thread_id if thread_id and thread_id.strip() else None,
        )

        html_answer = markdown.markdown(result["answer"])

        return templates.TemplateResponse(
            request=request,
            name="partials/chat_response.html",
            context={
                "result": result,
                "html_answer": html_answer,
                "user_question": message,
            },
        )

    except RuntimeError as e:
        error_msg = str(e)
        if "Remote LLM Server returned error status 400" in error_msg:
            return "<article style='border-color: red;'><strong>Context Window Exceeded:</strong> The combined length of your question and the retrieved documentation is too large.</article>"
        return f"<article style='border-color: red;'><strong>Internal Error:</strong> {error_msg}</article>"
