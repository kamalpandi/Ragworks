import asyncio
import json
import os
from typing import TYPE_CHECKING, AsyncIterator

import httpx
from langchain_community.llms.llamacpp import LlamaCpp
from langchain_core.callbacks import CallbackManager, StreamingStdOutCallbackHandler

from app.components.llms.base import BaseLLMProvider, LLMResponse
from app.core.config import settings
from app.observability.logger import get_logger

if TYPE_CHECKING:
    from app.services.llm_queue import LLMRequestQueue

logger = get_logger(__name__)

_llm_queue: "LLMRequestQueue | None" = None
_lock: asyncio.Lock | None = None


def _get_lock() -> asyncio.Lock:
    global _lock
    if _lock is None:
        _lock = asyncio.Lock()
    return _lock


async def _get_queue():
    global _llm_queue
    if _llm_queue is None:
        from app.services.llm_queue import LLMRequestQueue

        _llm_queue = LLMRequestQueue()
        await _llm_queue.start()
    return _llm_queue


class LlamaCppProvider(BaseLLMProvider):
    def __init__(self):
        self.remote_url = getattr(settings, "REMOTE_LLAMACPP_URL", None)

        remote_timeout = getattr(settings, "LLM_REMOTE_TIMEOUT", 60.0)
        connect_timeout = getattr(settings, "LLM_REMOTE_CONNECT_TIMEOUT", 10.0)
        self.timeout = httpx.Timeout(remote_timeout, connect=connect_timeout)

        self.max_tokens = getattr(settings, "LLM_MAX_TOKENS", 2000)
        self.stop_sequences = getattr(
            settings, "LLM_STOP_SEQUENCES", ["<|im_end|>", "<|im_start|>", " assistant"]
        )

        if self.remote_url:
            self.remote_url = self.remote_url.rstrip("/")
            logger.info("remote_url_found", url=self.remote_url)

            if self._check_connection():
                logger.info("remote_connection_success")
                self._llm = None
            else:
                logger.warning("remote_connection_failed_fallback")
                self.remote_url = None
                self._init_local_llm()
        else:
            logger.info("no_remote_url_configured")
            self._init_local_llm()

    def _init_local_llm(self):
        if not settings.LOCAL_MODEL or not os.path.exists(settings.LOCAL_MODEL):
            raise FileNotFoundError(
                f"Initialization Failed: Remote server was unreachable and "
                f"local model file does not exist at path: '{settings.LOCAL_MODEL}'"
            )

        logger.info("loading_local_model", model=settings.LOCAL_MODEL)

        n_ctx = getattr(settings, "LLM_N_CTX", 4000)
        top_p = getattr(settings, "LLM_TOP_P", 0.9)
        n_gpu_layers = getattr(settings, "LLM_N_GPU_LAYERS", -1)

        self._llm = LlamaCpp(
            model_path=settings.LOCAL_MODEL,
            temperature=settings.LLM_TEMP,
            max_tokens=self.max_tokens,
            n_ctx=n_ctx,
            stop=self.stop_sequences,
            top_p=top_p,
            callback_manager=CallbackManager([StreamingStdOutCallbackHandler()]),
            verbose=settings.DEBUG,
            n_gpu_layers=n_gpu_layers,
        )

    def _check_connection(self) -> bool:
        """Performs a synchronous ping to the llama.cpp server health endpoint."""
        health_timeout = getattr(settings, "LLM_HEALTH_CHECK_TIMEOUT", 3.0)
        try:
            with httpx.Client(timeout=health_timeout) as client:
                response = client.get(f"{self.remote_url}/health")
                if response.status_code == 200:
                    status_data = response.json()
                    return status_data.get("status") == "ok"
                return False
        except (httpx.RequestError, httpx.HTTPStatusError, json.JSONDecodeError):
            return False

    @property
    def provider_name(self) -> str:
        if self.remote_url:
            return f"remote-llamacpp/{self.remote_url}"
        return f"llamacpp/{settings.LOCAL_MODEL}"

    def _build_prompt(self, prompt: str, system: str) -> str:
        if system:
            return (
                f"<|im_start|>system\n{system}<|im_end|>\n"
                f"<|im_start|>user\n{prompt}<|im_end|>\n"
                f"<|im_start|>assistant\n"
            )
        return f"<|im_start|>user\n{prompt}<|im_end|>\n<|im_start|>assistant\n"

    async def complete(self, prompt: str, system: str = "") -> LLMResponse:
        full_prompt = self._build_prompt(prompt, system)

        # --- REMOTE PATH ---
        if self.remote_url:
            payload = {
                "prompt": full_prompt,
                "temperature": settings.LLM_TEMP,
                "n_predict": self.max_tokens,
                "stop": self.stop_sequences,
            }
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                try:
                    response = await client.post(
                        f"{self.remote_url}/completion", json=payload
                    )
                    response.raise_for_status()
                    content = response.json()["content"]
                    return LLMResponse(content=content, model="remote-llamacpp")
                except httpx.HTTPStatusError as e:
                    server_error_text = ""
                    try:
                        server_error_text = f" | Server Message: {e.response.json()['error']['message']}"
                    except Exception:
                        server_error_text = f" | Details: {e.response.text}"

                    logger.error(
                        "remote_api_error",
                        status=e.response.status_code,
                        error=str(e),
                    )
                    raise RuntimeError(
                        f"Remote LLM Server returned error status {e.response.status_code}.{server_error_text}"
                    )

        # --- LOCAL PATH ---
        if self._llm is None:
            raise RuntimeError("LlamaCpp local engine was not initialized.")

        queue = await _get_queue()
        loop = asyncio.get_event_loop()

        async def _invoke():
            return await loop.run_in_executor(
                None,
                lambda: self._llm.invoke(full_prompt),
            )

        content = await queue.submit(_invoke)

        if not content:
            raise ValueError("LlamaCpp returned an empty response.")

        return LLMResponse(content=content, model=settings.LOCAL_MODEL)

    async def stream(self, prompt: str, system: str = "") -> AsyncIterator[str]:
        full_prompt = self._build_prompt(prompt, system)

        # --- REMOTE PATH ---
        if self.remote_url:
            payload = {
                "prompt": full_prompt,
                "temperature": settings.LLM_TEMP,
                "n_predict": self.max_tokens,
                "stop": self.stop_sequences,
                "stream": True,
            }
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST", f"{self.remote_url}/completion", json=payload
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            try:
                                chunk_data = json.loads(line[6:])
                                content = chunk_data.get("content", "")
                                if content:
                                    yield content
                            except json.JSONDecodeError:
                                continue
            return

        # --- LOCAL PATH ---
        if self._llm is None:
            raise RuntimeError("LlamaCpp local engine was not initialized.")

        local_llm = self._llm
        lock = _get_lock()

        async with lock:
            loop = asyncio.get_event_loop()
            result_queue: asyncio.Queue[str | None] = asyncio.Queue()

            def _stream_to_queue():
                try:
                    for chunk in local_llm.stream(full_prompt):
                        loop.call_soon_threadsafe(result_queue.put_nowait, chunk)
                finally:
                    loop.call_soon_threadsafe(result_queue.put_nowait, None)

            loop.run_in_executor(None, _stream_to_queue)

            while True:
                chunk = await result_queue.get()
                if chunk is None:
                    break
                yield chunk
