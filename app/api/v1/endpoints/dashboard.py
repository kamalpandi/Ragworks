from fastapi import APIRouter, Request

from app.services.dashboard_service import get_dashboard, get_status

router = APIRouter()


@router.get("/status", summary="System status")
async def status():
    return await get_status()


@router.get("/dashboard", summary="Aggregate dashboard view model")
async def dashboard(request: Request):
    tenant_id = getattr(request.state, "tenant_id", "default")
    return await get_dashboard(tenant_id)
