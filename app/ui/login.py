from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse

from app.services.api_key_manager import validate_api_key
from app.ui import templates

router = APIRouter()


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    next_path = request.query_params.get("next", "/")
    return templates.TemplateResponse(
        request=request,
        name="pages/login.html",
        context={"next": next_path},
    )


@router.post("/login")
async def login_submit(api_key: str = Form(...), next_path: str = Form("/")):
    if not api_key or not api_key.strip():
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "API key is required"},
        )

    result = await validate_api_key(api_key.strip())

    if result is None:
        return JSONResponse(
            status_code=401,
            content={"success": False, "error": "Invalid API key"},
        )

    tenant_id, key_id = result
    return JSONResponse(
        status_code=200,
        content={
            "success": True,
            "api_key": api_key.strip(),
            "tenant_id": tenant_id,
        },
    )
