import markdown
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse

from app.components.query_translation.enricher import enrich_query
from app.core.dependencies import get_rag_engine
from app.core.prompt_loader import load_prompt
from app.services.conversation_service import get_thread
from app.ui import templates

router = APIRouter()


@router.post("/ui/query/chat", response_class=HTMLResponse)
async def ui_chat(
    request: Request,
    message: str = Form(...),
    file_name: str | None = Form(None),
    translation_strategy: str | None = Form(None),
    prompt_name: str | None = Form(None),
    thread_id: str | None = Form(None),
    engine=Depends(get_rag_engine),
    custom_prompt: str | None = Form(None),
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


@router.get("/ui/query/thread/{thread_id}", response_class=HTMLResponse)
async def load_thread(request: Request, thread_id: str):
    tenant_id = getattr(request.state, "tenant_id", "default")
    try:
        thread = await get_thread(tenant_id, thread_id)
    except Exception:
        return "<p style='color:var(--pico-muted-color);text-align:center;padding:2rem;'>Could not load conversation.</p>"

    if not thread.messages:
        return "<p style='color:var(--pico-muted-color);text-align:center;padding:2rem;'>Empty conversation.</p>"

    html_parts = []
    for msg in thread.messages:
        if msg.role == "user":
            html_parts.append(
                f'<article style="margin-bottom:0.5rem;"><header><small>You</small></header>'
                f"<p>{msg.content}</p></article>"
            )
        else:
            html_answer = markdown.markdown(msg.content)
            html_parts.append(
                f'<article style="margin-bottom:0.5rem;"><header><small>Assistant</small></header>'
                f'<div class="markdown-body">{html_answer}</div></article>'
            )

    return "\n".join(html_parts)
