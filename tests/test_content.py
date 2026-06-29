# tests/test_content.py
from app.content import uv, walk_calendar

def test_uv_primitives():
    assert uv({"stringValue": "hi"}) == "hi"
    assert uv({"integerValue": "5"}) == 5
    assert uv({"booleanValue": True}) is True
    assert uv({"arrayValue": {"values": [{"stringValue": "a"}]}}) == ["a"]
    assert uv({"mapValue": {"fields": {"k": {"stringValue": "v"}}}}) == {"k": "v"}

def test_walk_calendar_orders_and_skips_rest():
    data = {"w2": {"d1": {"wo": ["A", "rest"]}}, "w1": {"d3": {"wo": ["B"]}}}
    out = walk_calendar(data)
    assert out == [("B", "w1", "d3"), ("A", "w2", "d1")]
