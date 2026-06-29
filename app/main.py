# app/main.py
from pathlib import Path
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from . import config, fitbudd, verify, content, media
from .session import SessionStore
from .ratelimit import RateLimiter

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
sessions = SessionStore()
rl = RateLimiter(config.RL_LIMIT, config.RL_WINDOW)
WEB = Path(__file__).resolve().parent.parent / "web"

# NOTA: el frontend portado conserva el JS inline + handlers onclick del prototipo,
# por eso script-src incluye 'unsafe-inline' en v1. El XSS se mitiga con esc() (output
# encoding de todo texto de FitBudd) + el resto de defensas (tokens server-side, allowlist
# de media, HSTS, frame-options). Hardening futuro: externalizar JS y quitar onclick para
# poder volver a script-src 'self' estricto.
CSP = ("default-src 'self'; "
       "img-src 'self' https: data:; "
       "media-src 'self' https://*.b-cdn.net https://cdn-vod3.fitbudd.com blob:; "
       "connect-src 'self' https://*.b-cdn.net https://cdn-vod3.fitbudd.com; "
       "script-src 'self' 'unsafe-inline'; "
       # hls.js crea su demuxer en un Web Worker desde un blob: URL.
       "worker-src 'self' blob:; "
       "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
       "font-src 'self' https://fonts.gstatic.com https://cdn.shopify.com; "
       "frame-ancestors 'none'")

@app.middleware("http")
async def security_headers(request: Request, call_next):
    resp = await call_next(request)
    resp.headers["Content-Security-Policy"] = CSP
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["Referrer-Policy"] = "no-referrer"
    if config.IS_PROD:
        resp.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return resp

def _ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for", "")
    return xff.split(",")[0].strip() or (request.client.host if request.client else "0.0.0.0")

def _set_cookie(resp: Response, value: str):
    resp.set_cookie(config.SESSION_COOKIE, value, httponly=True, samesite="strict",
                    secure=config.IS_PROD, max_age=config.SESSION_TTL_SECONDS, path="/")

@app.post("/api/login")
async def login(request: Request):
    if not rl.allow(f"login:{_ip(request)}"):
        return JSONResponse({"error": "demasiados intentos, espera un momento"}, status_code=429)
    b = await request.json()
    try:
        out = await fitbudd.fitbudd_login(b.get("email", ""), b.get("password", ""))
    except Exception:
        return JSONResponse({"error": "credenciales invalidas"}, status_code=401)
    cookie = sessions.create(out["uid"], out["idToken"], out["refreshToken"])
    resp = JSONResponse({"ok": True})
    _set_cookie(resp, cookie)
    return resp

@app.post("/api/reset")
async def reset(request: Request):
    if not rl.allow(f"reset:{_ip(request)}"):
        return JSONResponse({"error": "demasiados intentos, espera un momento"}, status_code=429)
    b = await request.json()
    try:
        await fitbudd.fitbudd_reset(b.get("email", ""))
    except Exception:
        pass  # nunca filtrar fallas; respuesta SIEMPRE generica (H2)
    return JSONResponse({"ok": True})  # siempre generico (H2)

@app.post("/api/logout")
async def logout(request: Request):
    cookie = request.cookies.get(config.SESSION_COOKIE, "")
    if cookie:
        sessions.revoke(cookie)
    resp = JSONResponse({"ok": True})
    resp.delete_cookie(config.SESSION_COOKIE, path="/")
    return resp

async def _session_idtoken(request: Request):
    cookie = request.cookies.get(config.SESSION_COOKIE, "")
    sess = sessions.load(cookie) if cookie else None
    if not sess:
        return None, None
    try:
        claims = await verify.verify_id_token(sess["idToken"])
        return sess, claims["sub"]
    except verify.TokenError:
        try:
            ref = await fitbudd.fitbudd_refresh(sess["refreshToken"])
            new_cookie = sessions.create(ref["uid"], ref["idToken"], ref["refreshToken"])
            sessions.revoke(cookie)
            claims = await verify.verify_id_token(ref["idToken"])
            return {**sess, "idToken": ref["idToken"], "_new_cookie": new_cookie}, claims["sub"]
        except Exception:
            return None, None

@app.get("/api/session")
async def session_status(request: Request):
    # Sonda de "hay sesion?" para el load inicial — SIEMPRE 200 (evita un 401
    # rojo en consola cuando el usuario no ha entrado). No expone datos.
    sess, uid = await _session_idtoken(request)
    resp = JSONResponse({"authenticated": bool(sess and uid)})
    if sess and sess.get("_new_cookie"):
        _set_cookie(resp, sess["_new_cookie"])
    return resp

@app.get("/api/content")
async def get_content(request: Request):
    sess, uid = await _session_idtoken(request)
    if not sess or not uid:
        return JSONResponse({"error": "no autenticado"}, status_code=401)
    data = await content.build_content(sess["idToken"], uid)
    resp = JSONResponse(data)
    if sess.get("_new_cookie"):
        _set_cookie(resp, sess["_new_cookie"])
    return resp

@app.get("/api/playlist")
async def playlist(request: Request, vid: str = ""):
    sess, uid = await _session_idtoken(request)
    if not sess or not uid:
        return JSONResponse({"error": "no autenticado"}, status_code=401)
    try:
        text = await media.fetch_playlist(vid)
    except media.MediaError:
        return JSONResponse({"error": "no permitido"}, status_code=403)
    return Response(text, media_type="application/vnd.apple.mpegurl")

@app.get("/favicon.ico")
async def favicon():
    return FileResponse(WEB / "static" / "favicon.svg", media_type="image/svg+xml")

@app.get("/")
async def index():
    return HTMLResponse((WEB / "index.html").read_text(encoding="utf-8"))

app.mount("/static", StaticFiles(directory=str(WEB / "static")), name="static")
