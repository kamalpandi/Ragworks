import functools
from contextlib import contextmanager
from typing import Any, Callable

from app.core.config import settings

_tracer_provider = None
_tracer = None


def init_tracing(service_name: str = "rag-framework"):
    """Initialize OpenTelemetry tracing with the configured exporter."""
    if not settings.OBSERVABILITY_ENABLED:
        return

    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    global _tracer_provider, _tracer

    if settings.OTEL_EXPORTER_TYPE == "otlp":
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
            OTLPSpanExporter,
        )

        exporter = OTLPSpanExporter(endpoint=settings.OTEL_EXPORTER_ENDPOINT)
    elif settings.OTEL_EXPORTER_TYPE == "console":
        from opentelemetry.sdk.trace.export import ConsoleSpanExporter

        exporter = ConsoleSpanExporter()
    else:
        exporter = None

    if exporter:
        provider = TracerProvider()
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        _tracer_provider = provider

    _tracer = trace.get_tracer(service_name)


def get_tracer():
    global _tracer
    if _tracer is None and settings.OBSERVABILITY_ENABLED:
        init_tracing()
    return _tracer


def traced(name: str | None = None, attrs_fn: Callable[..., dict] | None = None):
    """Decorator to trace a function call as an OpenTelemetry span.

    Usage:
        @traced("rag.retrieve")
        async def retrieve(query): ...
    """

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            tracer = get_tracer()
            span_name = name or func.__name__
            if tracer is None:
                return await func(*args, **kwargs)

            attributes = attrs_fn(*args, **kwargs) if attrs_fn else {}
            with tracer.start_as_current_span(span_name, attributes=attributes):
                return await func(*args, **kwargs)

        return wrapper

    return decorator


@contextmanager
def trace_span(span_name: str, attributes: dict[str, Any] | None = None):
    """Context manager for inline span tracing.

    Usage:
        with trace_span("rag.rerank", {"top_n": 3}):
            chunks = await reranker.rerank(...)
    """
    tracer = get_tracer()
    if tracer is None:
        yield
        return

    with tracer.start_as_current_span(span_name, attributes=attributes or {}) as span:
        yield span
