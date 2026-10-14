import asyncio
import json
import logging
import os

import httpx

# Esta es la función que debe devolver la lista de objetos con esquemas
from client.data_mcp.discovery import discover_tools
from client.llm.mistral import generate_answer
from client.rag.profiler import PROFILER_PATH, get_cached_profile
from client.rag.retrieval import build_hierarchical_context, retrieve_chunks
from client.utils.settings import DATA_DIR, OLLAMA_URL

logger = logging.getLogger(__name__)


async def call_mistral(prompt: str, timeout: float = 80.0) -> str:
    """Llamada optimizada para CPU."""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                OLLAMA_URL,
                json={
                    "model": "llama3.2",
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                    "options": {
                        "num_predict": 100,
                        "temperature": 0,
                        "num_ctx": 4096,
                    },
                },
            )
            response.raise_for_status()
            return response.json().get("response", "").strip()
    except Exception as e:
        print(f"DEBUG: ❌ Mistral -> Error: {e}", flush=True)
        raise e


async def handle_query(query: str, call_tool_fn):
    print(f"\nDEBUG: 🚀 --- INICIO HANDLE_QUERY: '{query}' ---", flush=True)

    # 1. Obtener el perfil dinámico (Agnóstico)
    profile = get_cached_profile()
    # Si no hay perfil, usamos una descripción genérica para no romper el flujo
    profile_info = profile if profile else {"identidad": "Documento técnico general", "capacidades_rag": ["Consultas generales"]}

    try:
        tools_info = await asyncio.wait_for(discover_tools(), timeout=15.0)
    except Exception:
        tools_info = []

    # 2. Routing Basado en el Perfil (Sin reglas fijas de Nasdaq)
    router_prompt = f"""
[INST] <<SYS>>
Eres un Orquestador Lógico. Tu misión es elegir la ruta (RAG, TOOL, BOTH o NONE).
<</SYS>>

### 📖 PERFIL DEL DOCUMENTO DISPONIBLE:
{json.dumps(profile_info, indent=2)}

### 🛠️ HERRAMIENTAS MCP DISPONIBLES:
{json.dumps(tools_info, indent=2)}

### 🎯 INSTRUCCIONES DE DECISIÓN:
- Usa **RAG**: Si la consulta entra en las 'capacidades_rag' del perfil.
- Usa **TOOL**: Si la consulta se menciona en las 'fronteras_negativas' del perfil o requiere una herramienta MCP.
- Usa **BOTH**: Si necesitas extraer un dato del documento para usarlo en una herramienta (ej: convertir una cifra encontrada en el texto).
- Prioriza siempre el perfil para saber qué contiene el documento.

### ❓ CONSULTA: 
"{query}"

Responde exclusivamente con este JSON:
{{
  "route": "TOOL | RAG | BOTH | NONE",
  "reason": "Breve explicación basada en el perfil",
  "tool": "nombre_exacto_si_aplica",
  "args": {{ "arg1": "valor" }}
}} [/INST]"""

    try:
        decision_raw = await call_mistral(router_prompt)
        decision = json.loads(decision_raw[decision_raw.find("{"):decision_raw.rfind("}")+1])
        route = decision.get("route", "NONE")
        tool_name = decision.get("tool")
        tool_args = decision.get("args", {})
    except Exception as e:
        print(f"DEBUG: ⚠️ Error en decisión: {e}")
        route, tool_name, tool_args = "NONE", None, {}

    # --- EJECUCIÓN JERÁRQUICA ---
    rag_context = ""
    tool_result = ""
    response_data = {"route": route, "answer": "", "citations": [], "tool_calls": []}

    # PASO A: RAG (Nivel 1 y 2 - Requisito 4.2)
    if route in ["RAG", "BOTH"]:
        try:
            # Recuperación por similitud (Nivel 1) + Contexto ampliado (Nivel 2)
            chunks, _ = retrieve_chunks(query, k=5)
            rag_data = build_hierarchical_context(chunks)
            rag_context = rag_data["context"]
            response_data["citations"] = [f"Pág. {p}" for p in rag_data["pages"]]
        except Exception as e:
            print(f"DEBUG: ❌ RAG Error: {e}")

    # PASO B: TOOL (MCP vía SSE - Requisito 4.3)
    if route in ["TOOL", "BOTH"] and tool_name:
        
        # LÓGICA DE EXTRACCIÓN PARA BOTH (Caso T3)
        if route == "BOTH" and rag_context:
            print("DEBUG: 🔄 Ajustando argumentos de la Tool con datos del RAG...", flush=True)
            # Inyectamos el contexto del RAG en los argumentos para que la Tool o el LLM final operen
            tool_args["context_data"] = rag_context[:500] 

        try:
            res = await call_tool_fn(tool_name, tool_args)
            # El resultado se formatea para ser procesado por el LLM final
            tool_result = str(res)
            response_data["tool_calls"].append({
                "tool": tool_name, 
                "args": tool_args, 
                "result": tool_result
            })
        except Exception as e:
            tool_result = f"Error en tool: {e}"

    # PASO C: GENERACIÓN FINAL (Citación verificable - Punto 13)
    # Combinamos ambas fuentes. El LLM final decidirá cómo usar el dato de la Tool y la cita del PDF.
    final_context = f"CONTENIDO_PDF: {rag_context}\n\nRESULTADO_HERRAMIENTA: {tool_result}"
    response_data["answer"] = await generate_answer(query, final_context)

    return response_data
