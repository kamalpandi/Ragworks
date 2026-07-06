from prometheus_client import Counter, Gauge, Histogram, generate_latest, REGISTRY


_metrics_registry = REGISTRY

# RAG Pipeline Metrics
rag_queries_total = Counter(
    "rag_queries_total",
    "Total number of RAG queries processed",
    ["status"],
)

rag_pipeline_duration_seconds = Histogram(
    "rag_pipeline_duration_seconds",
    "End-to-end RAG pipeline latency",
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
)

rag_step_duration_seconds = Histogram(
    "rag_step_duration_seconds",
    "Duration per pipeline step",
    ["step"],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 15.0],
)

rag_retrieved_chunks = Histogram(
    "rag_retrieved_chunks",
    "Number of chunks retrieved before reranking",
    buckets=[1, 3, 5, 10, 20, 50],
)

rag_reranked_chunks = Histogram(
    "rag_reranked_chunks",
    "Number of chunks after reranking",
    buckets=[1, 2, 3, 5, 10],
)

rag_tokens_consumed = Counter(
    "rag_tokens_consumed",
    "Total tokens consumed by LLM",
    ["type"],
)

rag_active_requests = Gauge(
    "rag_active_requests",
    "Number of in-flight RAG requests",
)

# Rate Limiting
rag_rate_limit_exceeded_total = Counter(
    "rag_rate_limit_exceeded_total",
    "Total rate limit exceeded events",
    ["tenant_id", "operation"],
)

# LLM Queue
rag_llm_queue_depth = Gauge(
    "rag_llm_queue_depth",
    "Number of requests waiting in the LLM queue",
)

rag_llm_queue_timeout_total = Counter(
    "rag_llm_queue_timeout_total",
    "Total LLM queue timeout events",
)

# Usage Tracking
rag_usage_queries_total = Counter(
    "rag_usage_queries_total",
    "Total queries tracked by usage system",
    ["tenant_id"],
)

rag_usage_tokens_total = Counter(
    "rag_usage_tokens_total",
    "Total tokens tracked by usage system",
    ["tenant_id", "type"],
)


def init_metrics():
    """No-op; metrics are initialized at import time."""
    pass


def get_metrics_registry():
    return _metrics_registry


def get_metrics_response():
    """Return Prometheus text format metrics."""
    return generate_latest(_metrics_registry)
