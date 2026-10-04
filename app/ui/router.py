from fastapi import APIRouter

from app.ui import (
    eval_ui,
    prompts,
)

ui_router = APIRouter()

ui_router.include_router(prompts.router, tags=["UI Prompts"])
ui_router.include_router(eval_ui.router, tags=["UI Evaluation"])
