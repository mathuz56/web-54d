# app/fitbudd.py
import httpx
from . import config

_transport = None  # overridable en tests

class AuthError(Exception):
    pass

def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=30, transport=_transport,
                             headers={"User-Agent": config.UA, "Accept": "*/*"})

async def fitbudd_login(email: str, password: str) -> dict:
    async with _client() as c:
        r = await c.post(f"{config.BFF}/api/login",
                         json={"cid": config.CID, "email": email, "password": password},
                         headers={"fb-project": config.FB_PROJECT})
        data = r.json()
        if not data.get("success") or not data.get("token"):
            raise AuthError(data.get("message") or "login_failed")
        ex = await c.post(
            f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithCustomToken?key={config.FB_KEY}",
            json={"token": data["token"], "returnSecureToken": True})
        ex.raise_for_status()
        ej = ex.json()
        return {"idToken": ej["idToken"], "refreshToken": ej.get("refreshToken", ""),
                "uid": ej.get("localId") or data.get("uid")}

async def fitbudd_refresh(refresh_token: str) -> dict:
    async with _client() as c:
        r = await c.post(f"https://securetoken.googleapis.com/v1/token?key={config.FB_KEY}",
                         data={"grant_type": "refresh_token", "refresh_token": refresh_token})
        r.raise_for_status()
        j = r.json()
        return {"idToken": j["id_token"], "refreshToken": j["refresh_token"], "uid": j.get("user_id", "")}

async def fitbudd_reset(email: str) -> None:
    try:
        async with _client() as c:
            await c.post(f"{config.BFF}/api/mailResetLink",
                         json={"cid": config.CID, "email": email},
                         headers={"fb-project": config.FB_PROJECT})
    except Exception:
        pass  # nunca filtrar si el email existe (anti-enumeracion, H2)
