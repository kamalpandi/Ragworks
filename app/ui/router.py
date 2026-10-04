from fastapi import APIRouter

from app.ui import prompts

ui_router = APIRouter()

ui_router.include_router(prompts.router, tags=["UI Prompts"])
