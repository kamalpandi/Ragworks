import time
from collections import defaultdict

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.config import settings
from app.observability.logger import get_logger
from app.observability.metrics import rag_rate_limit_exceeded_total

logger = get_logger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self._buckets: dict[str, dict[str, list[float]]] = defaultdict(
            lambda: {"query": [], "ingest": []}
        )

    async def dispatch(self, request: Request, call_next):
        if not settings.RATE_LIMIT_ENABLED:
            return await call_next(request)

        tenant_id = getattr(request.state, "tenant_id", "anonymous")
        path = request.url.path

        if _is_query_path(path):
            operation = "query"
            limit = settings.RATE_LIMIT_QUERIES_PER_MINUTE
        elif _is_ingest_path(path):
            operation = "ingest"
            limit = settings.RATE_LIMIT_INGEST_PER_MINUTE
        else:
            return await call_next(request)

        burst = settings.RATE_LIMIT_BURST_SIZE
        now = time.time()
        window_start = now - 60

        timestamps = self._buckets[tenant_id][operation]
        timestamps[:] = [t for t in timestamps if t > window_start]

        if len(timestamps) >= limit + burst:
            oldest = timestamps[0] if timestamps else now
            retry_after = int(max(1, 60 - (now - oldest)))
            rag_rate_limit_exceeded_total.labels(
                tenant_id=tenant_id, operation=operation
            ).inc()
            logger.warning(
                "rate_limit_exceeded", tenant_id=tenant_id, operation=operation
            )
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "retry_after_seconds": retry_after,
                },
                headers={"Retry-After": str(retry_after)},
            )

        timestamps.append(now)
        return await call_next(request)


def _is_query_path(path: str) -> bool:
    return path == "/api/v1/query" or path == "/ui/query/chat"


def _is_ingest_path(path: str) -> bool:
    return path.startswith(("/api/v1/ingest", "/ui/ingest"))
