import pytest
from client.router import handle_query
from client.rag.index_pdf import build_index


# ---------- T1: RAG factual ----------
def test_rag_query_factual():
    query = "notificación de incidentes"
    resp = handle_query(query)

    assert resp["route"] == "RAG"
    assert "answer" in resp
    assert resp["citations"]
    assert all("page" in c for c in resp["citations"])


# ---------- T2: RAG resumen ----------
def test_rag_summary():
    query = "resume la notificación de incidentes"
    resp = handle_query(query)

    assert resp["route"] == "RAG"
    assert "answer" in resp
    assert resp["citations"]
    assert 1 <= len(resp["citations"]) <= 3


# ---------- T3: BOTH conversión ----------
def test_both_conversion_usd():
    query = "convierte el Producto Interior Bruto del documento a USD"
    resp = handle_query(query)

    assert resp["route"] == "BOTH"
    assert resp["citations"]
    assert resp["tool_calls"]
    tool = resp["tool_calls"][0]
    assert tool["tool"] == "fx_rate"
    assert tool["args"]["quote"] == "USD"
    assert "answer" in resp


def test_both_conversion_jpy():
    query = "convierte el Producto Interior Bruto del documento a JPY"
    resp = handle_query(query)

    assert resp["route"] == "BOTH"
    tool = resp["tool_calls"][0]
    assert tool["args"]["quote"] == "JPY"


# ---------- T5: NONE ----------
def test_none_query():
    query = "que hora es?"
    resp = handle_query(query)

    assert resp["route"] == "NONE"
    assert resp["answer"].startswith("La información no aparece")


# ---------- T6: AMBIGUOUS ----------
def test_ambiguous_query():
    query = "convierte el Producto Interior Bruto del documento"
    resp = handle_query(query)

    assert resp["route"] == "AMBIGUOUS"
    assert "ambigua" in resp["answer"].lower()


# ---------- Infra ----------
def test_reindex_pdf():
    # Solo verifica que no explota
    build_index(force=True)
    assert True
