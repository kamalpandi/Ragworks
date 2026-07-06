import asyncio
from typing import Any, Callable, Coroutine

from app.core.config import settings
from app.observability.logger import get_logger
from app.observability.metrics import rag_llm_queue_depth, rag_llm_queue_timeout_total

logger = get_logger(__name__)


class LLMRequestQueue:
    def __init__(self):
        self._queue: asyncio.Queue[
            tuple[asyncio.Future[Any], Callable[[], Coroutine[Any, Any, Any]]]
        ] = asyncio.Queue()
        self._worker_task: asyncio.Task[Any] | None = None
        self._timeout = settings.LLM_QUEUE_TIMEOUT_SECONDS

    async def start(self):
        if self._worker_task is None:
            self._worker_task = asyncio.create_task(self._worker())

    async def stop(self):
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
            self._worker_task = None

    async def submit(self, task: Callable[[], Coroutine[Any, Any, Any]]) -> Any:
        future: asyncio.Future[Any] = asyncio.Future()
        await self._queue.put((future, task))
        rag_llm_queue_depth.set(self._queue.qsize())

        try:
            return await asyncio.wait_for(future, timeout=self._timeout)
        except asyncio.TimeoutError:
            rag_llm_queue_timeout_total.inc()
            logger.warning("llm_queue_timeout", timeout_s=self._timeout)
            raise

    async def _worker(self):
        while True:
            try:
                future, task = await self._queue.get()
                rag_llm_queue_depth.set(self._queue.qsize())
                try:
                    result = await task()
                    if not future.done():
                        future.set_result(result)
                except Exception as e:
                    if not future.done():
                        future.set_exception(e)
            except asyncio.CancelledError:
                break
