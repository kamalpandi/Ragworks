from typing import Optional

from fastapi import APIRouter, Query

from app.models.log_entry import LogQuery
from app.observability.log_store import log_store

router = APIRouter()


@router.get("/")
async def query_logs(
    level: Optional[str] = Query(None),
    event: Optional[str] = Query(None),
    trace_id: Optional[str] = Query(None),
    request_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    since: Optional[str] = Query(None),
    until: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    q = LogQuery(
        level=level,
        event=event,
        trace_id=trace_id,
        request_id=request_id,
        search=search,
        since=since,
        until=until,
        limit=limit,
        offset=offset,
    )
    entries = await log_store.query(q)
    total = await log_store.count(q)
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "entries": [e.model_dump() for e in entries],
    }


@router.get("/stats")
async def log_stats():
    return await log_store.get_stats()
