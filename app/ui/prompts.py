from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

from app.core.prompt_loader import (
    delete_prompt,
    get_available_prompts,
    load_prompt,
    save_prompt,
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


@router.get("/ui/prompts/load", response_class=HTMLResponse)
async def htmx_prompts_list(request: Request):
    return _render_list(request)


@router.get("/ui/prompts/edit/{category}/{name}", response_class=HTMLResponse)
async def htmx_edit_form(request: Request, category: str, name: str):
    content = load_prompt(name, category)
    return templates.TemplateResponse(
        request=request,
        name="partials/prompt_edit.html",
        context={
            "name": name,
            "category": category,
            "content": content,
            "is_new": False,
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


@router.post("/ui/prompts/save", response_class=HTMLResponse)
async def htmx_save_prompt(request: Request):
    form = await request.form()
    name = str(form.get("name", "")).strip()
    content = str(form.get("content", ""))
    category = str(form.get("category", "system")).strip()
    is_new = form.get("is_new", "")

    if not name:
        raise HTTPException(status_code=400, detail="Prompt name is required")

    if name == "default" and category == "system" and not is_new:
        raise HTTPException(status_code=403, detail="Cannot overwrite default prompt")

    save_prompt(name, content, category)
    return _render_list(request)


@router.delete("/ui/prompts/delete/{category}/{name}", response_class=HTMLResponse)
async def htmx_delete_prompt(request: Request, category: str, name: str):
    if name == "default" and category == "system":
        raise HTTPException(status_code=403, detail="Cannot delete default prompt")
    delete_prompt(name, category)
    return _render_list(request)
