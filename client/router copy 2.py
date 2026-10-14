import re
import time
import requests
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from client.rag.retrieval import build_hierarchical_context, retrieve_chunks
from client.utils.settings import MCP_URL, ROUTER_LLM_MODEL

# =====================================================
# Lazy loading del LLM (NO se carga al arrancar)
# =====================================================
_model = None
_tokenizer = None


def get_llm():
    global _model, _tokenizer
    if _model is None:
        _tokenizer = AutoTokenizer.from_pretrained(ROUTER_LLM_MODEL)
        _model = AutoModelForCausalLM.from_pretrained(
            ROUTER_LLM_MODEL,
            device_map="auto",
            torch_dtype=torch.float16,
        )
    return _model, _tokenizer


# =====================================================
# TOOL DETECTION
# =====================================================
TOOL_KEYWORDS = {
    "fx_rate": [
        "convertir",
        "cambio",
        "divisa",
        "moneda",
        "€",
        "$",
        "¥",
        "eur",
        "usd",
        "yen",
        "libra",
    ],
    "market_status": ["abierto", "cerrado", "mercado", "hora"],
}


def detect_tool(query: str):
    q = query.lower()
    for tool, keywords in TOOL_KEYWORDS.items():
        if any(k in q for k in keywords):
            return tool
    return None


# =====================================================
# TOOL ARG EXTRACTION
# =====================================================
def extract_fx_args(query: str):
    q = query.upper()

    amount_match = re.search(r"([\d,.]+)", q)
    amount = float(amount_match.group(1).replace(",", "")) if amount_match else None

    currencies = re.findall(r"\b[A-Z]{3}\b", q)

    if len(currencies) >= 2:
        return {
            "base": currencies[0],
            "quote": currencies[1],
            "amount": amount,
        }

    return {"base": "EUR", "quote": "USD", "amount": amount}


def extract_market_args(query: str):
    words = re.findall(r"[A-Za-z]{3,}", query)
    stopwords = {"esta", "está", "abierto", "cerrado", "el", "la", "de", "en"}

    candidates = [w for w in words if w.lower() not in stopwords]
    return {"market": candidates[-1].lower()} if candidates else {"market": "default"}


def extract_tool_args(query: str, tool: str) -> dict:
    if tool == "fx_rate":
        return extract_fx_args(query)
    if tool == "market_status":
        return extract_market_args(query)
    return {}


# =====================================================
# MCP TOOL CALL
# =====================================================
def handle_tool(query: str, tool: str):
    args = extract_tool_args(query, tool)
    start = time.time()

    try:
        resp = requests.post(f"{MCP_URL}/call/{tool}", json=args, timeout=30)
        result = resp.json()
    except Exception as e:
        result = {"error": str(e)}

    return {
        "route": "TOOL",
        "tool": tool,
        "args": args,
        "duration_s": time.time() - start,
        "result": result,
    }


# =====================================================
# RAG
# =====================================================
def is_summary_query(query: str) -> bool:
    keywords = ["resumen", "resumir", "síntesis", "hazme un resumen"]
    return any(k in query.lower() for k in keywords)


def llm_summarize(context: str, max_tokens: int = 300):
    model, tokenizer = get_llm()

    prompt = f"""
Resume el siguiente contenido del documento de forma clara y concisa.
Incluye entre 1 y 3 referencias a páginas si es posible.

Contexto:
{context}
"""

    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    output = model.generate(
        **inputs,
        max_new_tokens=max_tokens,
        temperature=0.2,
        do_sample=False,
    )

    text = tokenizer.decode(output[0], skip_special_tokens=True)
    return text[len(prompt):].strip() if text.startswith(prompt) else text


def handle_rag(query: str, rag_results):
    docs_with_score, _ = rag_results
    context = build_hierarchical_context(docs_with_score)

    answer = (
        llm_summarize(context["context"])
        if is_summary_query(query)
        else context["context"]
    )

    return {
        "route": "RAG",
        "answer": answer,
        "pages": context["pages"][:3],
    }


# =====================================================
# DOCUMENT INTENT (CLAVE)
# =====================================================
def is_document_query(query: str) -> bool:
    q = query.lower()

    doc_usage_keywords = [
        "documento",
        "pdf",
        "texto",
        "según",
        "describe",
        "explica",
        "qué dice",
        "cómo se",
    ]

    summary_keywords = ["resumen", "resumir", "síntesis"]

    return any(k in q for k in doc_usage_keywords + summary_keywords)


# =====================================================
# BOTH
# =====================================================
def handle_both(query: str, rag_results, tool: str):
    return {
        "route": "BOTH",
        "rag": handle_rag(query, rag_results),
        "tool": handle_tool(query, tool),
    }


# =====================================================
# ROUTER PRINCIPAL
# =====================================================
def handle_query(query: str):
    tool = detect_tool(query)
    doc_intent = is_document_query(query)

    rag_results = retrieve_chunks(query) if doc_intent else None

    if doc_intent and tool:
        return handle_both(query, rag_results, tool)

    if tool and not doc_intent:
        return handle_tool(query, tool)

    if doc_intent:
        return handle_rag(query, rag_results)

    return {
        "route": "NONE",
        "answer": "La información no aparece en el documento ni requiere herramientas externas.",
    }
