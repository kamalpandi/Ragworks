from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse

from app.core.config import settings
from app.observability.logger import get_logger

logger = get_logger(__name__)


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        exempt = [p.strip() for p in settings.AUTH_EXEMPT_PATHS.split(",") if p.strip()]
        if path in exempt or path.startswith("/static"):
            request.state.tenant_id = "default"
            return await call_next(request)

        if not settings.AUTH_ENABLED:
            request.state.tenant_id = "default"
            return await call_next(request)

        api_key = _extract_api_key(request)

        admin_header = request.headers.get("X-Admin-Key", "")
        is_admin = admin_header and admin_header == settings.ADMIN_API_KEY
        if is_admin:
            request.state.is_admin = True

        if not api_key:
            if is_admin:
                request.state.tenant_id = "admin"
                return await call_next(request)
            if "text/html" in request.headers.get("Accept", ""):
                from urllib.parse import urlencode

                params = urlencode({"next": path})
                return RedirectResponse(url=f"/login?{params}", status_code=302)
            return JSONResponse(
                status_code=401,
                content={
                    "error": "Missing API key",
                    "detail": "Provide X-API-Key header or Authorization: Bearer <key>",
                },
            )

        from app.services.api_key_manager import validate_api_key

        result = await validate_api_key(api_key)
        if result is None:
            return JSONResponse(
                status_code=401,
                content={"error": "Invalid API key"},
            )

        tenant_id, key_id = result
        request.state.tenant_id = tenant_id
        request.state.api_key_id = key_id

        return await call_next(request)


def _extract_api_key(request: Request) -> str | None:
    api_key = request.headers.get("X-API-Key", "")
    if api_key:
        return api_key

    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:]

    return request.cookies.get("rag_api_key") or None
