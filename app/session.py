# app/session.py
import time, secrets, threading
from itsdangerous import TimestampSigner, BadSignature, SignatureExpired
from . import config

class SessionStore:
    def __init__(self):
        self._signer = TimestampSigner(config.SESSION_SECRET)
        self._lock = threading.Lock()
        self._store: dict[str, dict] = {}  # sid -> {uid,idToken,refreshToken,last}

    def create(self, uid: str, id_token: str, refresh_token: str) -> str:
        sid = secrets.token_urlsafe(24)
        with self._lock:
            self._store[sid] = {"uid": uid, "idToken": id_token,
                                "refreshToken": refresh_token, "last": time.time()}
        return self._signer.sign(sid.encode()).decode()

    def _read_sid(self, cookie_value: str) -> str | None:
        try:
            raw = self._signer.unsign(cookie_value, max_age=config.SESSION_TTL_SECONDS)
            return raw.decode()
        except (BadSignature, SignatureExpired):
            return None

    def load(self, cookie_value: str) -> dict | None:
        sid = self._read_sid(cookie_value)
        if not sid:
            return None
        with self._lock:
            rec = self._store.get(sid)
            if not rec:
                return None
            if time.time() - rec["last"] > config.SESSION_IDLE_SECONDS:
                self._store.pop(sid, None)
                return None
            rec["last"] = time.time()
            return {"sid": sid, **rec}

    def revoke(self, cookie_value: str) -> None:
        sid = self._read_sid(cookie_value)
        if not sid:
            return
        with self._lock:
            self._store.pop(sid, None)
