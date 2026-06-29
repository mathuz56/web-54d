# tests/test_frontend.py
from pathlib import Path
HTML = (Path(__file__).resolve().parent.parent / "web" / "index.html").read_text(encoding="utf-8")

def test_no_cdn_hls_uses_selfhosted():
    assert "cdn.jsdelivr.net" not in HTML
    assert "/static/hls.min.js" in HTML

def test_no_prefilled_credentials():
    assert "isaahck@gmail.com" not in HTML
    assert 'value="123456"' not in HTML

def test_uses_cookie_credentials_not_token_headers():
    assert "x-fb-token" not in HTML
    assert "credentials" in HTML  # fetch con credentials:'same-origin'

def test_playlist_endpoint_used():
    assert "/api/playlist?vid=" in HTML
