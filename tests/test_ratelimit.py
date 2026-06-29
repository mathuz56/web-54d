# tests/test_ratelimit.py
from app.ratelimit import RateLimiter

def test_allows_under_limit_then_blocks():
    rl = RateLimiter(limit=3, window=60)
    assert rl.allow("1.2.3.4") is True
    assert rl.allow("1.2.3.4") is True
    assert rl.allow("1.2.3.4") is True
    assert rl.allow("1.2.3.4") is False  # 4th in window -> blocked

def test_separate_keys_independent():
    rl = RateLimiter(limit=1, window=60)
    assert rl.allow("a") is True
    assert rl.allow("b") is True
    assert rl.allow("a") is False
