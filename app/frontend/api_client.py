"""In-process HTTP client for the backend JSON API.

The frontend reaches the backend exclusively through this client. It never
imports backend service, database, or model modules. ``httpx.ASGITransport``
delivers requests straight to the backend ASGI app without a network socket.
"""

from typing import Any

import httpx


class BackendClient:
    def __init__(self, app: Any, base_url: str = "http://backend"):
        self._client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url=base_url,
        )

    async def request(
        self, method: str, path: str, *, api_key: str | None = None, **kwargs: Any
    ) -> httpx.Response:
        headers = dict(kwargs.pop("headers", None) or {})
        if api_key:
            headers["X-API-Key"] = api_key
        return await self._client.request(method, path, headers=headers, **kwargs)

    async def get(
        self, path: str, *, api_key: str | None = None, **kwargs: Any
    ) -> httpx.Response:
        return await self.request("GET", path, api_key=api_key, **kwargs)

    async def post(
        self, path: str, *, api_key: str | None = None, **kwargs: Any
    ) -> httpx.Response:
        return await self.request("POST", path, api_key=api_key, **kwargs)

    async def put(
        self, path: str, *, api_key: str | None = None, **kwargs: Any
    ) -> httpx.Response:
        return await self.request("PUT", path, api_key=api_key, **kwargs)

    async def delete(
        self, path: str, *, api_key: str | None = None, **kwargs: Any
    ) -> httpx.Response:
        return await self.request("DELETE", path, api_key=api_key, **kwargs)

    async def aclose(self) -> None:
        await self._client.aclose()
