"""Page shells owned by the frontend.

Shells render the layout; their fragment content still comes from the
not-yet-migrated ``app/ui`` routes (different URLs) during the transition.
"""

from fastapi import APIRouter, Depends, Request

from app.frontend import templates
from app.frontend.deps import require_session

router = APIRouter()


@router.get("/")
async def dashboard_page(request: Request, _session=Depends(require_session)):
    return templates.TemplateResponse(request=request, name="pages/dashboard.html")


@router.get("/config")
async def config_page(request: Request, _session=Depends(require_session)):
    return templates.TemplateResponse(request=request, name="pages/config.html")


@router.get("/ingest")
async def ingest_page(request: Request, _session=Depends(require_session)):
    return templates.TemplateResponse(request=request, name="pages/ingest.html")
