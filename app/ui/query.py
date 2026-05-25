from typing import Optional

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse

from app.components.query_translation.enricher import enrich_query
from app.core.dependencies import get_rag_engine, load_prompt
from app.ui import templates

router = APIRouter()


@router.get("/query", response_class=HTMLResponse)
def query_page(request: Request):
    """Renders the main Chat/Query layout shell"""
    return templates.TemplateResponse(request=request, name="pages/query.html")


@router.post("/ui/query/chat", response_class=HTMLResponse)
async def ui_chat(
    request: Request,
    message: str = Form(...),
    file_name: str = Form(...),
    translation_strategy: Optional[str] = Form(None),
    prompt_name: Optional[str] = Form(None),
    engine=Depends(get_rag_engine),
):
    # 1. HTML Forms send empty strings instead of None, so we clean them up
    strategy = (
        translation_strategy
        if translation_strategy and translation_strategy.strip()
        else None
    )
    prompt = prompt_name if prompt_name and prompt_name.strip() else None

    # 2. Validation
    if not file_name.strip():
        return "<article style='background-color: var(--pico-form-element-invalid-active-border-color); color: white;'>❌ A valid target 'file_name' must be explicitly provided.</article>"

    # 3. Replicate API Core Logic
    system_report = load_prompt(prompt) if prompt else None
    enriched_query = enrich_query(message, file_name)

    try:
        # Call the RAG engine
        result = await engine.answer_question(
            query=enriched_query,
            file_filter=file_name,
            translation_strategy=strategy,
            system_prompt=system_report,
        )

        # Render the successful response partial
        return templates.TemplateResponse(
            request=request,
            name="partials/chat_response.html",
            context={"result": result},
        )

    except RuntimeError as e:
        error_msg = str(e)
        if "Remote LLM Server returned error status 400" in error_msg:
            return "<article style='border-color: red;'><strong>Context Window Exceeded:</strong> The combined length of your question and the retrieved documentation is too large.</article>"

        return f"<article style='border-color: red;'><strong>Internal Error:</strong> {error_msg}</article>"
