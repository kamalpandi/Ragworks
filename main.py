import asyncio
import uvicorn
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles

from app.api.v1.api import api_router
from app.core.config import settings
from app.middleware.auth import AuthMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.observability.logger import setup_logging
from app.observability.middleware import ObservabilityMiddleware
from app.observability.tracing import init_tracing
from app.ui.router import ui_router

init_tracing()
setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown logic for background services."""
    from app.core.pool import init_pool, close_pool
    from app.core.migrations import run_migrations

    await init_pool()
    await asyncio.to_thread(run_migrations)

    if settings.OBSERVABILITY_ENABLED:
        from app.observability.log_store import log_store

        await log_store.start()
    yield
    if settings.OBSERVABILITY_ENABLED:
        from app.observability.log_store import log_store

        await log_store.stop()

    await close_pool()


app = FastAPI(
    title="RAG Framework API",
    description="Modular RAG engine",
    version="1.0.0",
    debug=settings.DEBUG,
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.add_middleware(AuthMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(ObservabilityMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        o.strip() for o in settings.CORS_ALLOWED_ORIGINS.split(",") if o.strip()
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")
app.include_router(ui_router)


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    from app.observability.metrics import get_metrics_response

    return Response(content=get_metrics_response(), media_type="text/plain")


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.APP_RELOAD,
        workers=settings.APP_WORKERS,
    )
