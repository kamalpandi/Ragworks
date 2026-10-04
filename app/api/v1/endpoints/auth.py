from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/me", summary="Return the identity for the presented API key")
async def auth_me(request: Request):
    """Identity endpoint used by the frontend to validate a submitted key.

    Authentication is enforced by middleware before this handler runs, so a
    missing or invalid key never reaches here (HTTP 401 instead).
    """
    return {
        "tenant_id": getattr(request.state, "tenant_id", "default"),
        "key_id": getattr(request.state, "api_key_id", None),
    }
