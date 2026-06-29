# tests/test_static_mount.py
from fastapi.testclient import TestClient
from app import main
def test_static_served():
    c = TestClient(main.app)
    r = c.get("/static/hls.min.js")
    assert r.status_code == 200
