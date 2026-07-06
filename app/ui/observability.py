from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.observability.log_store import log_store
from app.ui import templates

router = APIRouter()


@router.get("/logs", response_class=HTMLResponse)
def logs_page(request: Request):
    return templates.TemplateResponse(request=request, name="pages/observability.html")


@router.get("/ui/logs/list", response_class=HTMLResponse)
async def htmx_logs_list(
    request: Request,
    level: str | None = None,
    search: str | None = None,
    limit: int = 50,
):
    from app.models.log_entry import LogQuery

    q = LogQuery(level=level, search=search, limit=limit)
    entries = await log_store.query(q)
    return templates.TemplateResponse(
        request=request,
        name="partials/log_viewer.html",
        context={"entries": entries, "level": level or "", "search": search or ""},
    )


@router.get("/ui/logs/stats", response_class=HTMLResponse)
async def htmx_logs_stats(request: Request):
    stats = await log_store.get_stats()
    return templates.TemplateResponse(
        request=request,
        name="partials/log_stats.html",
        context={"stats": stats},
    )
