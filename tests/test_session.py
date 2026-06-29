# tests/test_session.py
import pytest
from app.session import SessionStore

def test_create_load_roundtrip():
    s = SessionStore()
    cookie = s.create("UID1", "ID1", "RT1")
    data = s.load(cookie)
    assert data["uid"] == "UID1"
    assert data["idToken"] == "ID1"
    assert data["refreshToken"] == "RT1"

def test_revoked_session_returns_none():
    s = SessionStore()
    cookie = s.create("UID1", "ID1", "RT1")
    s.revoke(cookie)
    assert s.load(cookie) is None

def test_tampered_cookie_returns_none():
    s = SessionStore()
    cookie = s.create("UID1", "ID1", "RT1")
    assert s.load(cookie + "x") is None
