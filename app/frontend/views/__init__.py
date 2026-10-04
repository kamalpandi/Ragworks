"""Frontend view routers.

Routes are added here as domains migrate from ``app/ui`` (auth, pages,
dashboard, config, ingest, query, prompts, observability, eval).
"""

from fastapi import APIRouter

from app.frontend.views import auth, config, dashboard, ingest, pages, query

router = APIRouter()

router.include_router(auth.router)
router.include_router(pages.router)
router.include_router(dashboard.router)
router.include_router(config.router)
router.include_router(ingest.router)
router.include_router(query.router)
