import pytest
from client.router import handle_query


# ---------- T1: RAG factual ----------
def test_rag_factual():
    q = "qué es la notificación de incidentes"
    r = handle_query(q)

    assert r["route"] == "RAG"
    assert len(r["answer"]) > 50

    # Validamos citas correctamente
    assert "citations" in r
    assert len(r["citations"]) >= 1
    assert all("page" in c for c in r["citations"])


# ---------- T2: RAG resumen ----------
def test_rag_summary():
    q = "hazme un resumen de la notificación de incidentes"
    r = handle_query(q)

    assert r["route"] == "RAG"
    assert "-" in r["answer"]  # formato resumen

    # 1–3 citas relevantes
    assert "citations" in r
    assert 1 <= len(r["citations"]) <= 3
    assert all("page" in c for c in r["citations"])


# ---------- Robustez: contenido real del PDF ----------
def test_rag_mentions_pib():
    q = "cual es el impacto económico del Producto Interior Bruto"
    r = handle_query(q)

    assert r["route"] == "RAG"
    assert any("p.i.b." in c["text"].lower() for c in r["citations"])
