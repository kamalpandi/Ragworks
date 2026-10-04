from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.testclient import TestClient

from app.frontend.deps import get_csrf_token, verify_pre_session_csrf

app = FastAPI()


@app.get("/login")
async def login_page(request: Request):
    return HTMLResponse(f'<meta name="csrf-token" content="{get_csrf_token(request)}">')


@app.post("/login")
async def login_submit(request: Request):
    if not verify_pre_session_csrf(request):
        return JSONResponse(
            {"error": "missing/invalid pre-session csrf"}, status_code=403
        )
    return {"ok": True}


def _extract_token(html: str) -> str:
    return html.split('content="')[1].split('"')[0]


def test_login_requires_pre_session_csrf():
    client = TestClient(app)
    assert client.post("/login").status_code == 403


def test_login_accepts_valid_pre_session_csrf():
    client = TestClient(app)
    token = _extract_token(client.get("/login").text)
    response = client.post("/login", headers={"X-CSRF-Token": token})
    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_login_token_is_single_use():
    client = TestClient(app)
    token = _extract_token(client.get("/login").text)
    assert client.post("/login", headers={"X-CSRF-Token": token}).status_code == 200
    assert client.post("/login", headers={"X-CSRF-Token": token}).status_code == 403
