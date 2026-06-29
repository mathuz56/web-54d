# tests/test_fitbudd.py
import httpx, pytest
from app import fitbudd

@pytest.mark.asyncio
async def test_login_success(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/login":
            return httpx.Response(200, json={"success": True, "token": "CUSTOM", "uid": "U1"})
        if "signInWithCustomToken" in str(request.url):
            return httpx.Response(200, json={"idToken": "ID1", "refreshToken": "RT1", "localId": "U1"})
        return httpx.Response(404)
    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(fitbudd, "_transport", transport)
    out = await fitbudd.fitbudd_login("a@b.com", "pw")
    assert out == {"idToken": "ID1", "refreshToken": "RT1", "uid": "U1"}

@pytest.mark.asyncio
async def test_login_bad_credentials(monkeypatch):
    def handler(request): return httpx.Response(200, json={"success": False, "message": "bad"})
    monkeypatch.setattr(fitbudd, "_transport", httpx.MockTransport(handler))
    with pytest.raises(fitbudd.AuthError):
        await fitbudd.fitbudd_login("a@b.com", "wrong")
