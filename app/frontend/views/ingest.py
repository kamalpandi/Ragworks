"""Ingest fragment views (frontend).

Form providers render static partials; the POST handlers forward to the
backend ingest API via ``api_client`` and render a status/error span.
"""

from fastapi import APIRouter, Depends, Request

from app.frontend import templates
from app.frontend.deps import require_session

router = APIRouter()


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
