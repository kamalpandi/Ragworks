from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Query, Request

from app.core.pool import get_pool

router = APIRouter()


@router.get("", summary="Get usage statistics for the requesting tenant")
async def get_usage(
    request: Request,
    days: int = Query(
        default=30, ge=1, le=365, description="Number of days to aggregate"
    ),
):
    tenant_id = getattr(request.state, "tenant_id", "default")
    since = datetime.now(UTC) - timedelta(days=days)

    pool = get_pool()
    async with pool.connection() as conn, conn.cursor() as cur:
        await cur.execute(
            "SELECT operation, COUNT(*) AS count, "
            "COALESCE(SUM(tokens_prompt), 0) AS total_prompt_tokens, "
            "COALESCE(SUM(tokens_completion), 0) AS total_completion_tokens, "
            "COALESCE(SUM(chunks_created), 0) AS total_chunks_created "
            "FROM usage_logs "
            "WHERE tenant_id = %s AND created_at >= %s "
            "GROUP BY operation",
            [tenant_id, since],
        )
        rows = await cur.fetchall()

        summary = {
            "tenant_id": tenant_id,
            "period_days": days,
            "since": since.isoformat(),
            "operations": {},
            "totals": {
                "total_queries": 0,
                "total_ingests": 0,
                "total_prompt_tokens": 0,
                "total_completion_tokens": 0,
                "total_chunks_created": 0,
            },
        }

        for row in rows:
            op = row["operation"]
            summary["operations"][op] = {
                "count": row["count"],
                "total_prompt_tokens": row["total_prompt_tokens"],
                "total_completion_tokens": row["total_completion_tokens"],
                "total_chunks_created": row["total_chunks_created"],
            }
            if op == "query":
                summary["totals"]["total_queries"] = row["count"]
            elif op == "ingest":
                summary["totals"]["total_ingests"] = row["count"]
            summary["totals"]["total_prompt_tokens"] += row["total_prompt_tokens"]
            summary["totals"]["total_completion_tokens"] += row[
                "total_completion_tokens"
            ]
            summary["totals"]["total_chunks_created"] += row["total_chunks_created"]

        return summary
