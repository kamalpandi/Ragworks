from fastapi import APIRouter

from app.ui import (
    eval_ui,
    observability,
    prompts,
)

ui_router = APIRouter()

ui_router.include_router(prompts.router, tags=["UI Prompts"])
ui_router.include_router(observability.router, tags=["UI Observability"])
ui_router.include_router(eval_ui.router, tags=["UI Evaluation"])
