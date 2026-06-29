# tests/test_app.py
import httpx, pytest
from fastapi.testclient import TestClient
from app import main, fitbudd, verify, content, media

@pytest.fixture
def client(monkeypatch):
    async def fake_login(email, password):
        if password == "good":
            return {"idToken": "ID1", "refreshToken": "RT1", "uid": "UID1"}
        raise fitbudd.AuthError("bad")
    async def fake_verify(tok): return {"sub": "UID1"}
    async def fake_content(idt, uid): return {"name": "Ej", "uid_used": uid, "calendar": []}
    monkeypatch.setattr(main.fitbudd, "fitbudd_login", fake_login)
    monkeypatch.setattr(main.verify, "verify_id_token", fake_verify)
    monkeypatch.setattr(main.content, "build_content", fake_content)
    return TestClient(main.app)

def test_login_bad_is_generic_401(client):
    r = client.post("/api/login", json={"email": "a@b.com", "password": "wrong"})
    assert r.status_code == 401
    assert "inv" in r.json()["error"].lower()

def test_login_good_sets_cookie_then_content(client):
    r = client.post("/api/login", json={"email": "a@b.com", "password": "good"})
    assert r.status_code == 200
    assert main.config.SESSION_COOKIE in r.cookies or "set-cookie" in {k.lower() for k in r.headers}
    r2 = client.get("/api/content")
    assert r2.status_code == 200
    assert r2.json()["uid_used"] == "UID1"   # uid del token verificado, no del cliente

def test_content_without_cookie_401(client):
    r = client.get("/api/content")
    assert r.status_code == 401

def test_session_probe_is_200_unauthenticated(client):
    # la sonda de carga inicial nunca debe 401 (evita error rojo en consola)
    r = client.get("/api/session")
    assert r.status_code == 200
    assert r.json()["authenticated"] is False

def test_session_probe_true_after_login(client):
    client.post("/api/login", json={"email": "a@b.com", "password": "good"})
    r = client.get("/api/session")
    assert r.status_code == 200
    assert r.json()["authenticated"] is True

def test_security_headers_present(client):
    r = client.get("/api/content")
    assert r.headers.get("X-Frame-Options") == "DENY"
    assert "content-security-policy" in {k.lower() for k in r.headers}

def test_reset_always_generic_200(client, monkeypatch):
    async def boom(email): raise RuntimeError("should be swallowed")
    monkeypatch.setattr(main.fitbudd, "fitbudd_reset", boom)
    r = client.post("/api/reset", json={"email": "x@y.com"})
    assert r.status_code == 200
