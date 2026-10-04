import logging
from datetime import UTC

import structlog

from app.core.config import settings


def _db_processor(logger, method_name, event_dict):
    """structlog processor that enqueues log events for DB storage.

    Runs synchronously in the logging call chain. The LogStore background
    task drains the queue and writes to PostgreSQL asynchronously.
    """
    if not settings.OBSERVABILITY_ENABLED:
        return event_dict

    try:
        from app.observability.log_store import log_store

        level = event_dict.get("level", "info").upper()
        event_name = event_dict.get("event", "")
        extra = {
            k: v
            for k, v in event_dict.items()
            if k
            not in (
                "event",
                "level",
                "logger",
                "timestamp",
                "message",
                "trace_id",
                "request_id",
            )
        }
        # Serialize non-JSON-safe values to strings
        safe_extra = {}
        for k, v in extra.items():
            if isinstance(v, (str, int, float, bool, list, dict, type(None))):
                safe_extra[k] = v
            else:
                safe_extra[k] = str(v)

        import uuid
        from datetime import datetime

        entry = {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.now(UTC),
            "level": level,
            "logger_name": event_dict.get("logger", ""),
            "event": event_name or "",
            "trace_id": event_dict.get("trace_id"),
            "request_id": event_dict.get("request_id"),
            "message": str(event_dict.get("_from_structlog", "")),
            "extra": safe_extra,
        }
        log_store.enqueue(entry)
    except Exception:
        pass

    return event_dict


def setup_logging():
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        _db_processor,
    ]

    if settings.LOG_FORMAT == "json":
        processors = shared_processors + [
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ]
    else:
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True),
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    level = getattr(logging, settings.LOG_LEVEL)
    logging.basicConfig(format="%(message)s", level=level)
    for name in ["uvicorn", "uvicorn.access", "uvicorn.error"]:
        logging.getLogger(name).handlers = []
        logging.getLogger(name).propagate = True


def get_logger(name: str = __name__) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)


if settings.OBSERVABILITY_ENABLED:
    setup_logging()
