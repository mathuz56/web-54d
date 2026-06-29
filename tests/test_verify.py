# tests/test_verify.py
import time, jwt, pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from app import verify, config

@pytest.fixture
def keypair():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pub_pem = key.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
    return key, pub_pem

@pytest.mark.asyncio
async def test_valid_token(monkeypatch, keypair):
    key, pub_pem = keypair
    monkeypatch.setattr(verify, "_get_public_key", lambda kid: pub_pem)
    tok = jwt.encode(
        {"sub": "UID9", "aud": config.FB_PROJECT,
         "iss": f"https://securetoken.google.com/{config.FB_PROJECT}",
         "exp": int(time.time()) + 600, "iat": int(time.time())},
        key, algorithm="RS256", headers={"kid": "k1"})
    claims = await verify.verify_id_token(tok)
    assert claims["sub"] == "UID9"

@pytest.mark.asyncio
async def test_wrong_audience(monkeypatch, keypair):
    key, pub_pem = keypair
    monkeypatch.setattr(verify, "_get_public_key", lambda kid: pub_pem)
    tok = jwt.encode({"sub": "X", "aud": "other", "exp": int(time.time())+600},
                     key, algorithm="RS256", headers={"kid": "k1"})
    with pytest.raises(verify.TokenError):
        await verify.verify_id_token(tok)
