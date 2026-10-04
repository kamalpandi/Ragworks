"""Ingest fragment views (frontend).

Form providers render static partials; the POST handlers verify the session
CSRF token, forward to the backend ingest API via ``api_client``, and render a
status/error span.
"""

import logging

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse

from app.frontend import templates
from app.frontend.deps import (
    get_backend_client,
    require_session,
    verify_session_csrf,
)

logger = logging.getLogger("rag_framework.frontend.ingest")

router = APIRouter()


def _ok(message: str) -> HTMLResponse:
    return HTMLResponse(f"<span style='color: var(--pico-ins-color);'>{message}</span>")


def _err(message: str) -> HTMLResponse:
    # Rendered as 200 so HTMX swaps the span into the target element.
    return HTMLResponse(f"<span style='color: var(--pico-del-color);'>{message}</span>")


def _detail_or(resp, fallback: str) -> str:
    try:
        payload = resp.json()
    except ValueError:
        return fallback
    detail = payload.get("detail") if isinstance(payload, dict) else None
    if isinstance(detail, dict):
        return detail.get("message") or detail.get("error") or fallback
    if isinstance(detail, str):
        return detail
    return fallback


def _handle_failure(resp, fallback: str) -> HTMLResponse:
    if resp.status_code >= 500:
        logger.warning(
            "ingest_forward_failed", status=resp.status_code, body=resp.text[:200]
        )
        return _err("Ingest failed. Please try again.")
    return _err(_detail_or(resp, fallback))


@router.get("/ui/ingest/form/file")
async def get_file_form(request: Request, _session=Depends(require_session)):
    return templates.TemplateResponse(
        request=request, name="partials/ingest/file_form.html"
    )


@router.get("/ui/ingest/form/url")
async def get_url_form(request: Request, _session=Depends(require_session)):
    return templates.TemplateResponse(
        request=request, name="partials/ingest/url_form.html"
    )


@router.get("/ui/ingest/form/custom")
async def get_custom_form(request: Request, _session=Depends(require_session)):
    return templates.TemplateResponse(
        request=request, name="partials/ingest/custom_form.html"
    )


@router.post("/ui/ingest/url")
async def ui_ingest_url(
    request: Request,
    url: str = Form(...),
    session=Depends(require_session),
):
    verify_session_csrf(request, session)
    resp = await get_backend_client(request).post(
        "/api/v1/ingest/url", api_key=session.api_key, json={"url": url}
    )
    if resp.status_code >= 400:
        return _handle_failure(resp, "Could not extract text from URL.")
    data = resp.json()
    return _ok(f"URL extraction for '{data.get('url') or url}' started!")


@router.post("/ui/ingest/custom")
async def ui_ingest_custom(
    request: Request,
    text: str = Form(...),
    session=Depends(require_session),
):
    verify_session_csrf(request, session)
    resp = await get_backend_client(request).post(
        "/api/v1/ingest/custom", api_key=session.api_key, json={"texts": [text]}
    )
    if resp.status_code >= 400:
        return _handle_failure(resp, "Custom text ingestion failed.")
    return _ok("Custom text successfully ingested!")
