# web.54d.com — Portal de video de miembros 54D

Portal web donde los miembros entran con su cuenta FitBudd y ven SUS videos /
programas / calendario. App **FastAPI** (Python) lista para Docker + Traefik.

- **Auth:** login/refresh/reset contra FitBudd; el `idToken` se verifica server-side (JWKS).
- **Sesión:** cookie `HttpOnly` firmada; los tokens viven server-side (no en el navegador). Logout revoca server-side.
- **Video:** el server reescribe la playlist HLS a URLs absolutas de Bunny; los segmentos los baja el navegador **directo de Bunny** (sin relay, anti-SSRF, allowlist de hosts).
- **Seguridad:** rate-limit por IP, headers (CSP, HSTS, X-Frame-Options), errores genéricos.

## Estructura

```
app/        código FastAPI (ratelimit, fitbudd, verify, session, content, media, main)
web/        frontend (index.html + static: hls.min.js, favicon.svg)
tests/      pytest (25 tests)
Dockerfile  imagen (uvicorn :8099)
docker-compose.yml   stack Traefik para web.54d.com
```

## Correr local (dev)

```bash
python -m venv .venv && . .venv/Scripts/activate   # (Windows: .venv\Scripts\activate)
pip install -r requirements.txt
SESSION_SECRET=dev ENV=dev uvicorn app.main:app --port 8099
# http://127.0.0.1:8099
pytest -q     # 25 tests
```

## Deploy (Docker + Traefik / Portainer)

1. Genera un secreto de sesión:
   ```bash
   python -c "import secrets;print(secrets.token_urlsafe(48))"
   ```
2. Ajusta en `docker-compose.yml` el nombre real de tu **red Traefik** (label
   `traefik.docker.network` + `networks:`) y de tu **certResolver**
   (`tls.certresolver`) si difieren de `traefik` / `le`.
3. Despliega con tu secreto en el entorno:
   ```bash
   SESSION_SECRET=<tu-secreto> docker compose up -d --build
   ```
   o crea el Stack en Portainer (build desde este repo, variable `SESSION_SECRET`).
4. Verifica `https://web.54d.com` (TLS válido).

## Variables de entorno

| Var | Default | Notas |
|-----|---------|-------|
| `SESSION_SECRET` | (dev inseguro) | **OBLIGATORIA en prod.** Firma la cookie de sesión. |
| `ENV` | `dev` | `prod` activa cookie `secure` + HSTS. |
| `SESSION_TTL_SECONDS` | 604800 (7d) | Vida máxima de la sesión. |
| `SESSION_IDLE_SECONDS` | 43200 (12h) | Inactividad antes de expirar. |
| `RL_LIMIT` / `RL_WINDOW` | 15 / 60 | Rate-limit login/reset por IP. |
