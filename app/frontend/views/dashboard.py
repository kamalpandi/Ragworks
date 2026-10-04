"""Dashboard fragment views.

Each fragment fetches its data from the JSON API via ``api_client`` and
renders a partial. No backend imports.
"""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request

from app.frontend import templates
from app.frontend.deps import get_backend_client, require_session

router = APIRouter()


def _db_status_color(status: str) -> str:
    if status in ("connected", "running", "available"):
        return "var(--pico-ins-color)"
    if status in ("disconnected", "error", "unavailable"):
        return "var(--pico-del-color)"
    return "var(--pico-muted-color)"


@router.get("/ui/dashboard/status")
async def dashboard_status(request: Request, session=Depends(require_session)):
    client = get_backend_client(request)
    key = session.api_key
    status = (await client.get("/api/v1/status", api_key=key)).json()
    config = (await client.get("/api/v1/config", api_key=key)).json()["config"]
    db_status = status["database"]
    return templates.TemplateResponse(
        request=request,
        name="partials/dashboard_status.html",
        context={
            "app_host": config["APP_HOST"],
            "app_port": config["APP_PORT"],
            "db_status": db_status,
            "db_status_color": _db_status_color(db_status),
            "llm_provider": config["LLM_PROVIDER"],
            "llm_model": config["LLM_MODEL"],
            "doc_count": status["documents"],
            "key_count": status["api_keys"],
            "vector_provider": status["vector_provider"],
            "updated": datetime.now(UTC).strftime("%H:%M:%S"),
        },
    )
