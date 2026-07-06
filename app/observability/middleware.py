import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = structlog.get_logger(__name__)


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """Binds trace_id/request_id to structlog context for the request lifecycle."""

    async def dispatch(self, request: Request, call_next) -> Response:
        trace_id = request.headers.get("X-Trace-Id", str(uuid.uuid4()))
        request_id = request.headers.get("X-Request-Id", str(uuid.uuid4()))
        request.state.trace_id = trace_id
        request.state.request_id = request_id

        structlog.contextvars.bind_contextvars(
            trace_id=trace_id,
            request_id=request_id,
        )

        start_time = time.time()
        status_code = 500

        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            duration = time.time() - start_time
            logger.info(
                "request completed",
                method=request.method,
                path=request.url.path,
                status_code=status_code,
                duration_ms=round(duration * 1000, 2),
            )
            structlog.contextvars.unbind_contextvars("trace_id", "request_id")
            # Inject trace header on the response when available
            if "response" in locals():
                response.headers["X-Trace-Id"] = trace_id
                response.headers["X-Request-Id"] = request_id
