"""Frontend view routers.

Domain view routers (auth, pages, dashboard, config, ingest, query, prompts,
observability, eval) are aggregated here.
"""

from fastapi import APIRouter

from app.frontend.views import (
    auth,
    config,
    dashboard,
    eval,
    ingest,
    observability,
    pages,
    prompts,
    query,
)

router = APIRouter()

router.include_router(auth.router)
router.include_router(pages.router)
router.include_router(dashboard.router)
router.include_router(config.router)
router.include_router(ingest.router)
router.include_router(query.router)
router.include_router(observability.router)
router.include_router(eval.router)
router.include_router(prompts.router)
