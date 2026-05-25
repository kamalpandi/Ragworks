from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.core.config import settings
from app.ui import templates

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    """Renders the main layout shell"""
    return templates.TemplateResponse(request=request, name="pages/dashboard.html")


@router.get("/config", response_class=HTMLResponse)
def config_page(request: Request):
    """Renders the main Config layout shell"""
    return templates.TemplateResponse(request=request, name="pages/config.html")


@router.get("/ui/config/data", response_class=HTMLResponse)
def htmx_config_data(request: Request):
    """Returns the config data HTML snippet for HTMX"""
    # We can pass the settings directly to Jinja2
    return templates.TemplateResponse(
        request=request,
        name="partials/config_data.html",
        context={"settings": settings},
    )
