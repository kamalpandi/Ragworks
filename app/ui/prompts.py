from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.core.prompt_loader import get_available_prompts, load_prompt
from app.ui import templates

router = APIRouter()


@router.get("/prompts", response_class=HTMLResponse)
async def prompts_page(request: Request):
    return templates.TemplateResponse(request=request, name="pages/prompts.html")


@router.get("/ui/prompts/load", response_class=HTMLResponse)
async def htmx_prompts_list(request: Request):
    system_prompts = get_available_prompts("system")
    user_prompts = get_available_prompts("user")

    system_data = [
        {"name": p, "content": load_prompt(p, "system")} for p in system_prompts
    ]
    user_data = [{"name": p, "content": load_prompt(p, "user")} for p in user_prompts]

    return templates.TemplateResponse(
        request=request,
        name="partials/prompts_list.html",
        context={
            "system_prompts": system_data,
            "user_prompts": user_data,
        },
    )
