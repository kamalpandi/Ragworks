from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

from app.core.prompt_loader import (
    delete_prompt,
    get_available_prompts,
    load_prompt,
)
from app.ui import templates

router = APIRouter()


def _render_list(request: Request) -> HTMLResponse:
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


@router.get("/ui/prompts/new", response_class=HTMLResponse)
async def htmx_new_form(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="partials/prompt_edit.html",
        context={
            "name": "",
            "category": "system",
            "content": "",
            "is_new": True,
        },
    )


@router.delete("/ui/prompts/delete/{category}/{name}", response_class=HTMLResponse)
async def htmx_delete_prompt(request: Request, category: str, name: str):
    if name == "default" and category == "system":
        raise HTTPException(status_code=403, detail="Cannot delete default prompt")
    delete_prompt(name, category)
    return _render_list(request)
