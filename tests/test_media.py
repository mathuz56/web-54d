# tests/test_media.py
import pytest
from app import media

def test_host_allowed():
    assert media.host_allowed("https://cdn-vod3.fitbudd.com/x/playlist.m3u8") is True
    assert media.host_allowed("https://vz-29a74080-910.b-cdn.net/abc/720.m3u8") is True
    assert media.host_allowed("http://cdn-vod3.fitbudd.com/x") is False   # no https
    assert media.host_allowed("https://evil.com/x") is False
    assert media.host_allowed("file:///etc/passwd") is False
    assert media.host_allowed("https://169.254.169.254/latest/meta-data") is False

def test_rewrite_playlist_makes_absolute():
    text = "#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=1\n720/playlist.m3u8\nseg0.ts\n"
    final = "https://vz-29a74080-910.b-cdn.net/guid/master.m3u8"
    out = media.rewrite_playlist(text, final)
    assert "https://vz-29a74080-910.b-cdn.net/guid/720/playlist.m3u8" in out
    assert "https://vz-29a74080-910.b-cdn.net/guid/seg0.ts" in out
