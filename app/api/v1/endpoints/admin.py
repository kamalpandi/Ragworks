from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.services.api_key_manager import create_api_key, deactivate_api_key

router = APIRouter()


class CreateApiKeyRequest(BaseModel):
    tenant_id: str = Field(..., description="Tenant ID for the new API key")
    label: str = Field(default="", description="Human-readable label for the key")


class CreateApiKeyResponse(BaseModel):
    raw_key: str
    key_id: str
    tenant_id: str
    message: str = "Store this key securely. It will not be shown again."


def require_admin(request: Request):
    if not getattr(request.state, "is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "Admin access required",
                "detail": "Provide X-Admin-Key header",
            },
        )


@router.post(
    "/api-keys",
    response_model=CreateApiKeyResponse,
    summary="Create a new API key (admin-only)",
)
async def admin_create_api_key(body: CreateApiKeyRequest, request: Request):
    require_admin(request)
    raw_key, key_id = await create_api_key(tenant_id=body.tenant_id, label=body.label)
    return CreateApiKeyResponse(
        raw_key=raw_key, key_id=key_id, tenant_id=body.tenant_id
    )


@router.delete("/api-keys/{key_id}", summary="Deactivate an API key (admin-only)")
async def admin_delete_api_key(key_id: str, request: Request):
    require_admin(request)
    success = await deactivate_api_key(key_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="API key not found"
        )
    return {"status": "deactivated", "key_id": key_id}
