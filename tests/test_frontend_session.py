from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.core.sessions import InMemorySessionStore
from app.frontend.csrf import PreSessionTokenStore, tokens_match
from app.frontend.deps import require_session


def _request(session_store=None, cookies=None, headers=None, path="/"):
    state = SimpleNamespace()
    if session_store is not None:
        state.session_store = session_store
    app = SimpleNamespace(state=state)
    return SimpleNamespace(
        app=app,
        cookies=cookies or {},
        headers=headers or {},
        url=SimpleNamespace(path=path),
    )


def test_create_and_get():
    store = InMemorySessionStore(ttl_seconds=60)
    session = store.create("key-123", "tenant-a")
    assert session.api_key == "key-123"
    assert session.tenant_id == "tenant-a"
    assert session.csrf_token
    assert store.get(session.session_id) is session


def test_expiry_returns_none():
    store = InMemorySessionStore(ttl_seconds=60)
    session = store.create("key", "tenant-a", ttl_seconds=-1)
    assert store.get(session.session_id) is None


def test_delete():
    store = InMemorySessionStore()
    session = store.create("key", "tenant-a")
    store.delete(session.session_id)
    assert store.get(session.session_id) is None


def test_cleanup_removes_only_expired():
    store = InMemorySessionStore()
    store.create("k1", "tenant-a", ttl_seconds=-1)
    store.create("k2", "tenant-a", ttl_seconds=60)
    assert store.cleanup() == 1


def test_pre_session_token_single_use():
    store = PreSessionTokenStore(ttl_seconds=60)
    token = store.issue()
    assert store.verify_and_consume(token) is True
    assert store.verify_and_consume(token) is False


def test_pre_session_token_expired():
    store = PreSessionTokenStore(ttl_seconds=-1)
    assert store.verify_and_consume(store.issue()) is False


def test_pre_session_token_missing():
    store = PreSessionTokenStore()
    assert store.verify_and_consume(None) is False


def test_tokens_match():
    assert tokens_match("abc", "abc") is True
    assert tokens_match("abc", "abd") is False
    assert tokens_match(None, "abc") is False
    assert tokens_match("abc", None) is False


def test_require_session_redirects_htmx_with_header():
    with pytest.raises(HTTPException) as exc:
        require_session(_request(headers={"HX-Request": "true"}, path="/query"))
    assert exc.value.status_code == 200
    assert exc.value.headers["HX-Redirect"] == "/login"


def test_require_session_redirects_browser():
    with pytest.raises(HTTPException) as exc:
        require_session(_request(path="/query"))
    assert exc.value.status_code == 302
    assert exc.value.headers["Location"].startswith("/login")
