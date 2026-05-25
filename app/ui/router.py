from fastapi import APIRouter

from app.ui import config, dashboard, ingest, query

ui_router = APIRouter()

ui_router.include_router(dashboard.router, tags=["UI Dashboard"])
ui_router.include_router(config.router, tags=["UI Configuration"])
ui_router.include_router(ingest.router, tags=["UI Ingestion"])
ui_router.include_router(query.router, tags=["UI Query"])
