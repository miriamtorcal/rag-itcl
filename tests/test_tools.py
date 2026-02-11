import pytest
from client.router import handle_query


# ---------- T4: TOOL market ----------
def test_tool_market_open():
    q = "¿Está abierto el mercado nikkei?"
    r = handle_query(q)

    assert r["route"] == "TOOL"
    assert r["tool_calls"]
    tool = r["tool_calls"][0]
    assert tool["tool"] == "market_status"
    assert "is_open" in tool["result"]


def test_tool_market_closed():
    q = "mercado nasdaq cerrado"
    r = handle_query(q)

    assert r["route"] == "TOOL"
    tool = r["tool_calls"][0]
    assert tool["tool"] == "market_status"


# ---------- TOOL fx sin documento ----------
def test_tool_fx_only():
    q = "convierte EUR a USD"
    r = handle_query(q)

    assert r["route"] == "TOOL"
    tool = r["tool_calls"][0]
    assert tool["tool"] == "fx_rate"
    assert tool["args"]["base"] == "EUR"
    assert tool["args"]["quote"] == "USD"


# ---------- Robustez ----------
def test_tool_fx_unknown_currency_defaults():
    q = "convierte dinero a USD"
    r = handle_query(q)

    assert r["route"] in ["TOOL", "AMBIGUOUS"]
