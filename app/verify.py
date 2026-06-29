# app/verify.py
import time, jwt, httpx
from cryptography import x509
from cryptography.hazmat.primitives import serialization
from . import config

class TokenError(Exception):
    pass

_CERTS_URL = "https://www.googleapis.com/robot/v1/metadata/x509/securetoken@system.gserviceaccount.com"
_cache: dict = {"exp": 0, "keys": {}}

def _get_public_key(kid: str) -> bytes:
    # cache simple por TTL; devuelve PEM de clave publica para el kid
    if _cache["exp"] < time.time() or kid not in _cache["keys"]:
        resp = httpx.get(_CERTS_URL, timeout=15)
        resp.raise_for_status()
        keys = {}
        for k, cert_pem in resp.json().items():
            cert = x509.load_pem_x509_certificate(cert_pem.encode())
            keys[k] = cert.public_key().public_bytes(
                serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
        _cache["keys"] = keys
        _cache["exp"] = time.time() + 3600
    if kid not in _cache["keys"]:
        raise TokenError("unknown_kid")
    return _cache["keys"][kid]

async def verify_id_token(id_token: str) -> dict:
    try:
        header = jwt.get_unverified_header(id_token)
        pub = _get_public_key(header.get("kid", ""))
        claims = jwt.decode(
            id_token, pub, algorithms=["RS256"],
            audience=config.FB_PROJECT,
            issuer=f"https://securetoken.google.com/{config.FB_PROJECT}",
            options={"require": ["exp", "iat", "sub"]})
    except TokenError:
        raise
    except Exception as e:
        raise TokenError(str(e))
    if not claims.get("sub"):
        raise TokenError("no_sub")
    return claims
