"""Query views owned by the frontend.

Reaches the backend through ``api_client`` only: chat POST and thread
history GET. Query enrichment and system-prompt resolution already live in
the API layer, so these handlers stay thin.
"""

import logging

import markdown
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from app.frontend import templates
from app.frontend.deps import get_backend_client, require_session

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/ui/query/thread/{thread_id}", response_class=HTMLResponse)
async def ui_query_thread(
    request: Request, thread_id: str, session=Depends(require_session)
):
    resp = await get_backend_client(request).get(
        f"/api/v1/conversations/{thread_id}", api_key=session.api_key
    )
    if resp.status_code >= 400:
        logger.warning(
            "thread_load_failed status=%s body=%s",
            resp.status_code,
            resp.text[:200],
        )
        return templates.TemplateResponse(
            request=request,
            name="partials/thread_history.html",
            context={"messages": [], "unavailable": True},
        )

    messages = resp.json().get("messages", [])
    for msg in messages:
        if msg.get("role") != "user":
            msg["html"] = markdown.markdown(msg.get("content", ""))

    return templates.TemplateResponse(
        request=request,
        name="partials/thread_history.html",
        context={"messages": messages},
    )
