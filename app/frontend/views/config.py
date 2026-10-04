"""Config fragment view.

Renders the curated frontend config returned by ``/api/v1/config``; the raw
backend ``settings`` object is no longer passed to templates.
"""

from fastapi import APIRouter, Depends, Request

from app.frontend import templates
from app.frontend.deps import get_backend_client, require_session

router = APIRouter()


@router.get("/ui/config/data")
async def config_data(request: Request, session=Depends(require_session)):
    client = get_backend_client(request)
    data = (await client.get("/api/v1/config", api_key=session.api_key)).json()
    return templates.TemplateResponse(
        request=request,
        name="partials/config_data.html",
        context={"settings": data["config"]},
    )
