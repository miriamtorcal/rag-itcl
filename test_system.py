# tests/test_system.py
import pytest
from client.router import handle_query

@pytest.mark.asyncio
async def test_router_rag_logic():
    # T1: Pregunta factual sobre el PDF
    res = await handle_query("¿Cuál es el protocolo de contención?", lambda x, y: None)
    assert res["route"] in ["RAG", "BOTH"]
    assert "Pág." in res["citations"][0]

@pytest.mark.asyncio
async def test_router_tool_logic():
    # T4: Estado de mercado
    res = await handle_query("¿Está abierto Nasdaq?", lambda x, y: "Abierto")
    assert res["route"] == "TOOL"
    assert any(tc["tool"] == "market_status" for tc in res["tool_calls"])

@pytest.mark.asyncio
async def test_hybrid_flow():
    # T3: Caso híbrido
    res = await handle_query("Convierte el presupuesto a USD", lambda x, y: "Rate: 1.1")
    assert res["route"] == "BOTH"