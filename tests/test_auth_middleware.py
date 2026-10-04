import asyncio

import httpx

from main import app


def _get(path, headers):
    async def run():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://t", follow_redirects=False
        ) as client:
            return await client.get(path, headers=headers)

    return asyncio.run(run())


def test_frontend_htmx_unauthenticated_gets_hx_redirect():
    response = _get("/ui/dashboard/status", {"HX-Request": "true"})
    assert response.status_code == 200
    assert response.headers.get("HX-Redirect") == "/login"


def test_frontend_browser_unauthenticated_redirects_to_login():
    response = _get("/ui/dashboard/status", {"Accept": "text/html"})
    assert response.status_code == 302
    assert response.headers["Location"].startswith("/login")


def test_api_unauthenticated_returns_json_401():
    response = _get("/api/v1/status", {})
    assert response.status_code == 401
    assert response.headers.get("HX-Redirect") is None
    assert response.json()["error"] == "Missing API key"


def test_api_ignores_htmx_and_html_accept():
    response = _get("/api/v1/status", {"HX-Request": "true", "Accept": "text/html"})
    assert response.status_code == 401
    assert response.headers.get("HX-Redirect") is None
    assert "Location" not in response.headers
