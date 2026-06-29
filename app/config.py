import os

CID = "54donline"
# Firebase web API key de la app de miembros — PUBLICA (client key, no es secreto).
FB_KEY = "AIzaSyDIThzet3rQvCiqRk_0cvFz4vek59Pz2i4"
FB_PROJECT = "fitbudd-prod-v1"
BFF = "https://bff.fitbudd.com"
FS = f"https://firestore.googleapis.com/v1/projects/{FB_PROJECT}/databases/(default)/documents"
UA = "Mozilla/5.0 (54D-WebPortal)"

# Allowlist dura de hosts de video (anti-SSRF). Solo estos, solo https.
ALLOWED_VIDEO_HOSTS = ("cdn-vod3.fitbudd.com",)
ALLOWED_VIDEO_SUFFIXES = (".b-cdn.net",)

# Secreto de firma de la cookie de sesion (env en prod; default solo dev).
SESSION_SECRET = os.environ.get("SESSION_SECRET", "dev-only-insecure-change-me")
SESSION_COOKIE = "p54_session"
SESSION_TTL_SECONDS = int(os.environ.get("SESSION_TTL_SECONDS", str(7 * 24 * 3600)))
SESSION_IDLE_SECONDS = int(os.environ.get("SESSION_IDLE_SECONDS", str(12 * 3600)))

# Rate limit
RL_LIMIT = int(os.environ.get("RL_LIMIT", "15"))
RL_WINDOW = int(os.environ.get("RL_WINDOW", "60"))

IS_PROD = os.environ.get("ENV", "dev") == "prod"
