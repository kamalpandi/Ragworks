import asyncio

import httpx
import psycopg
import pytest
import pytest_asyncio

from app.core.config import settings
from app.core.migrations import run_migrations
from app.core.pool import close_pool, get_pool, init_pool
from app.services.api_key_manager import create_api_key, deactivate_api_key
from app.services.dashboard_service import get_dashboard, get_usage_stats
from app.services.llm_queue import LLMRequestQueue
from app.services.usage_tracker import track_ingest, track_query
from main import app


class TestMultiTenancy:
    """Integration tests for tenant-scoped data isolation.
    Requires PGVector to be running.
    """

    @pytest.mark.asyncio
    async def test_cross_tenant_isolation(self):
        """Tenant A and Tenant B should not see each other's data."""


class TestApiAuthentication:
    """Integration tests for API key auth middleware.
    Requires running FastAPI test client.
    """

    @pytest.mark.asyncio
    async def test_valid_api_key_grants_access(self):
        pass

    @pytest.mark.asyncio
    async def test_invalid_api_key_returns_401(self):
        pass

    @pytest.mark.asyncio
    async def test_missing_api_key_returns_401(self):
        pass

    @pytest.mark.asyncio
    async def test_exempt_paths_accessible(self):
        """Metrics, docs, openapi.json, health should be accessible without auth."""


class TestRateLimiting:
    """Integration tests for rate limiting."""

    @pytest.mark.asyncio
    async def test_rate_limit_exceeded_returns_429(self):
        pass

    @pytest.mark.asyncio
    async def test_retry_after_header(self):
        pass

    @pytest.mark.asyncio
    async def test_tenant_rate_limit_isolation(self):
        pass


class TestLLMQueue:
    """Unit tests for LLM request queue."""

    @pytest.mark.asyncio
    async def test_queue_serializes_concurrent_calls(self):
        queue = LLMRequestQueue()
        await queue.start()
        order = []

        async def task_a():
            order.append("a_start")
            await asyncio.sleep(0.1)
            order.append("a_end")
            return "a"

        async def task_b():
            order.append("b_start")
            await asyncio.sleep(0.1)
            order.append("b_end")
            return "b"

        result_a = asyncio.create_task(queue.submit(task_a))
        await asyncio.sleep(0.01)
        result_b = asyncio.create_task(queue.submit(task_b))

        a, b = await asyncio.gather(result_a, result_b)
        assert a == "a"
        assert b == "b"
        assert order == ["a_start", "a_end", "b_start", "b_end"]
        await queue.stop()

    @pytest.mark.asyncio
    async def test_queue_respects_timeout(self):
        settings.LLM_QUEUE_TIMEOUT_SECONDS = 0.1
        queue = LLMRequestQueue()
        await queue.start()

        async def slow_task():
            await asyncio.sleep(1)
            return "slow"

        async def fast_task():
            return "fast"

        r1 = asyncio.create_task(queue.submit(fast_task))
        await asyncio.sleep(0.01)
        r2 = asyncio.create_task(queue.submit(slow_task))
        await asyncio.sleep(0.01)

        with pytest.raises(asyncio.TimeoutError):
            await queue.submit(slow_task)

        result = await r1
        assert result == "fast"

        r2.cancel()
        await queue.stop()


class TestConversationMemory:
    """Integration tests for conversation memory.
    Requires PGVector to be running.
    """

    @pytest.mark.asyncio
    async def test_thread_stores_and_retrieves_messages(self):
        pass

    @pytest.mark.asyncio
    async def test_cross_tenant_thread_isolation(self):
        pass


def _postgres_available() -> bool:
    try:
        with psycopg.connect(settings.DATABASE_URL, connect_timeout=2):
            return True
    except (psycopg.Error, OSError):
        return False


@pytest_asyncio.fixture
async def db():
    """Provide a migrated connection pool, or skip when Postgres is absent."""
    if not _postgres_available():
        pytest.skip("PostgreSQL/PGVector not available; run the Docker container")
    await init_pool()
    await asyncio.to_thread(run_migrations)
    try:
        yield
    finally:
        await close_pool()


async def _clear_usage(tenant_id: str) -> None:
    pool = get_pool()
    async with pool.connection() as conn, conn.cursor() as cur:
        await cur.execute("DELETE FROM usage_logs WHERE tenant_id = %s", [tenant_id])


async def _seed_query(tenant_id: str, prompt: int, completion: int) -> None:
    pool = get_pool()
    async with pool.connection() as conn, conn.cursor() as cur:
        await cur.execute(
            "INSERT INTO usage_logs "
            "(tenant_id, operation, tokens_prompt, tokens_completion, chunks_retrieved) "
            "VALUES (%s, 'query', %s, %s, 0)",
            [tenant_id, prompt, completion],
        )


async def _seed_ingest(tenant_id: str, chunks: int) -> None:
    pool = get_pool()
    async with pool.connection() as conn, conn.cursor() as cur:
        await cur.execute(
            "INSERT INTO usage_logs "
            "(tenant_id, operation, chunks_created, source_name) "
            "VALUES (%s, 'ingest', %s, %s)",
            [tenant_id, chunks, "seed.pdf"],
        )


async def _api_get(path: str, api_key: str) -> httpx.Response:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.get(path, headers={"X-API-Key": api_key})


class TestUsageTracking:
    """Integration tests for usage aggregation against a live database."""

    @pytest.mark.asyncio
    async def test_usage_logs_created_after_query(self, db):
        tenant = "test-usage-write"
        await _clear_usage(tenant)

        await track_query(
            tenant, tokens_prompt=500, tokens_completion=200, chunks_retrieved=3
        )
        await track_ingest(tenant, chunks_created=50, source_name="seed.pdf")

        stats = await get_usage_stats(tenant)
        assert stats["query_count"] == 1
        assert stats["ingest_count"] == 1
        assert stats["total_tokens"] == 700
        assert stats["chunks_created"] == 50

        dashboard = await get_dashboard(tenant)
        assert dashboard["stats"] == stats

    @pytest.mark.asyncio
    async def test_usage_endpoint_returns_correct_aggregation(self, db):
        tenant = "test-usage-api"
        other = "test-usage-other"
        await _clear_usage(tenant)
        await _clear_usage(other)

        await _seed_query(tenant, prompt=100, completion=50)
        await _seed_query(tenant, prompt=200, completion=25)
        await _seed_ingest(tenant, chunks=10)
        await _seed_query(other, prompt=999, completion=999)

        raw_key, key_id = await create_api_key(tenant, label="usage-test")
        try:
            response = await _api_get("/api/v1/usage?days=1", raw_key)
        finally:
            await deactivate_api_key(key_id)

        assert response.status_code == 200
        body = response.json()
        assert body["totals"]["total_queries"] == 2
        assert body["totals"]["total_ingests"] == 1
        assert body["totals"]["total_prompt_tokens"] == 300
        assert body["totals"]["total_completion_tokens"] == 75
        assert body["totals"]["total_chunks_created"] == 10
        assert body["operations"]["query"]["count"] == 2

    @pytest.mark.asyncio
    async def test_dashboard_endpoint_populated_returns_stats(self, db):
        tenant = "test-dashboard-api"
        await _clear_usage(tenant)

        await _seed_query(tenant, prompt=100, completion=50)
        await _seed_ingest(tenant, chunks=7)

        raw_key, key_id = await create_api_key(tenant, label="dashboard-test")
        try:
            response = await _api_get("/api/v1/dashboard", raw_key)
        finally:
            await deactivate_api_key(key_id)

        # Regression: this returned 500 with a populated usage_logs table.
        assert response.status_code == 200
        stats = response.json()["stats"]
        assert stats["query_count"] == 1
        assert stats["ingest_count"] == 1
        assert stats["total_tokens"] == 150
        assert stats["chunks_created"] == 7
