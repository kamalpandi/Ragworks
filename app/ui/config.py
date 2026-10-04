from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.core.config import settings
from app.ui import templates

router = APIRouter()


@router.get("/ui/config/data", response_class=HTMLResponse)
def htmx_config_data(request: Request):
    """Returns the config data HTML snippet for HTMX"""
    # We can pass the settings directly to Jinja2
    return templates.TemplateResponse(
        request=request,
        name="partials/config_data.html",
        context={"settings": settings},
    )
