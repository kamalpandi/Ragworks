import asyncio

import httpx

from main import app


def _get(headers):
    async def run():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://t", follow_redirects=False
        ) as client:
            return await client.get("/ui/dashboard/status", headers=headers)

    return asyncio.run(run())


def test_htmx_unauthenticated_gets_hx_redirect():
    response = _get({"HX-Request": "true"})
    assert response.status_code == 200
    assert response.headers.get("HX-Redirect") == "/login"


def test_browser_unauthenticated_redirects_to_login():
    response = _get({"Accept": "text/html"})
    assert response.status_code == 302
    assert response.headers["Location"].startswith("/login")
