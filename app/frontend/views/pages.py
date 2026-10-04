"""Page shells owned by the frontend.

Shells render the layout; their fragment content is loaded from frontend
fragments, which in turn reach the backend over the JSON API.
"""

from fastapi import APIRouter, Depends, Request

from app.frontend import templates
from app.frontend.deps import get_backend_client, require_session

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


@router.get("/logs")
async def logs_page(request: Request, _session=Depends(require_session)):
    return templates.TemplateResponse(request=request, name="pages/observability.html")


@router.get("/eval")
async def eval_page(request: Request, session=Depends(require_session)):
    client = get_backend_client(request)
    key = session.api_key
    metrics = (await client.get("/api/v1/eval/metrics", api_key=key)).json()["metrics"]
    threads = (await client.get("/api/v1/conversations", api_key=key)).json()["threads"]
    return templates.TemplateResponse(
        request=request,
        name="pages/eval.html",
        context={"metrics": metrics, "threads": threads},
    )


@router.get("/query")
async def query_page(request: Request, session=Depends(require_session)):
    client = get_backend_client(request)
    key = session.api_key
    prompts = (await client.get("/api/v1/prompts", api_key=key)).json()[
        "system_prompts"
    ]
    files = (await client.get("/api/v1/ingest/files", api_key=key)).json()["sources"]
    threads = (await client.get("/api/v1/conversations", api_key=key)).json()["threads"]
    return templates.TemplateResponse(
        request=request,
        name="pages/query.html",
        context={
            "available_prompts": prompts,
            "available_files": files,
            "threads": threads,
        },
    )


@router.get("/prompts")
async def prompts_page(request: Request, _session=Depends(require_session)):
    return templates.TemplateResponse(request=request, name="pages/prompts.html")
