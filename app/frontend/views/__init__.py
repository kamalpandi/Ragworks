"""Frontend view routers.

Routes are added here as domains migrate from ``app/ui`` (auth, pages,
dashboard, config, ingest, query, prompts, observability, eval).
"""

from fastapi import APIRouter

from app.frontend.views import auth

router = APIRouter()

router.include_router(auth.router)
