import re
import time
import requests
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

from client.rag.retrieval import retrieve_chunks, build_hierarchical_context
from client.utils.settings import MCP_URL


STOPWORDS_3 = {
    "DEL",
    "LOS",
    "LAS",
    "POR",
    "CON",
    "PAR",
    "UNA",
    "UNO",
    "QUE",
    "EST",
    "DOC",
}



# TOOL DETECTION
def detect_tool(query: str):
    q = query.lower()
    if any(k in q for k in ["abierto", "cerrado", "bolsa", "mercado"]):
        return "market_status"
    if any(k in q for k in ["convertir", "divisa", "moneda", "eur", "usd", "€", "$"]):
        return "fx_rate"
    return None


def extract_market_args(query: str):
    words = re.findall(r"[A-Za-z]{3,}", query)
    stop = {"esta", "está", "abierto", "cerrado", "el", "la", "de", "en"}
    candidates = [w for w in words if w.lower() not in stop]
    return {"market": candidates[-1].lower()} if candidates else {"market": "default"}


def extract_amount_from_text(text: str):
    """
    Extrae cantidades tipo:
    - 1.163.663M €
    - 1163663 M EUR
    - 0,07%
    """
    # 1) Cantidades monetarias con sufijo
    money_pattern = r"([\d\.,]+)\s*(m|mm|bn)?\s*(€|eur|usd|\$)?"
    matches = re.findall(money_pattern, text.lower())

    for value, scale, currency in matches:
        try:
            number = float(value.replace(".", "").replace(",", "."))
        except ValueError:
            continue

        if scale == "m":
            number *= 1_000_000
        elif scale == "mm":
            number *= 1_000_000_000
        elif scale == "bn":
            number *= 1_000_000_000

        return number

    return None


def extract_fx_args(query: str, context_text: str | None = None):
    amount = None

    text = query.lower()
    if context_text:
        text += " " + context_text.lower()

    # detectar cifras tipo 1.163.663M €
    m = re.search(r"([\d\.,]+)\s*(m|millones|b)?\s*(€|eur|usd|\$)?", text)
    if m:
        num = m.group(1)
        mult = m.group(2)

        try:
            value = float(num.replace(".", "").replace(",", "."))
            if mult in ("m", "millones"):
                value *= 1_000_000
            elif mult == "b":
                value *= 1_000_000_000
            amount = value
        except:
            amount = None

    currencies = re.findall(r"\b[A-Z]{3}\b", query.upper())

    base = currencies[0] if currencies else "EUR"
    quote = currencies[1] if len(currencies) > 1 else "USD"

    return {"base": base, "quote": quote, "amount": amount}


def call_tool(tool: str, query: str, context_text: str | None = None):
    if tool == "market_status":
        args = extract_market_args(query)
    else:
        args = extract_fx_args(query, context_text)

    start = time.time()

    try:
        resp = requests.post(f"{MCP_URL}/call/{tool}", json=args, timeout=15)
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


def is_document_query(query: str):
    q = query.lower()
    return any(
        k in q
        for k in [
            "documento",
            "pdf",
            "según",
            "qué es",
            "explica",
            "describe",
            "notificación",
            "resumen",
        ]
    )


def handle_rag(query: str):
    docs, _ = retrieve_chunks(query)
    context = build_hierarchical_context(docs)

    if "resumen" in query.lower():
        answer = summarize(context, query)
    else:
        answer = answer_factual(context)

    return {
        "route": "RAG",
        "answer": answer,
        "pages": context["pages"][:3],
    }


def summarize(context: dict, query: str):
    """
    Resumen extractivo robusto (sin LLM)
    """
    text = context["context"]
    pages = context["pages"]

    # palabras clave desde la query
    keywords = set(w.lower() for w in re.findall(r"\w+", query) if len(w) > 4)

    sentences = re.split(r"(?<=[.!?])\s+", text)

    scored = []
    for s in sentences:
        s_clean = s.strip()
        if len(s_clean) < 60 or len(s_clean) > 300:
            continue

        score = sum(1 for kw in keywords if kw in s_clean.lower())
        if score > 0:
            scored.append((score, s_clean))

    # ordenar por relevancia
    scored.sort(key=lambda x: x[0], reverse=True)

    selected = [s for _, s in scored[:6]]

    # fallback si no hay suficientes
    if len(selected) < 3:
        selected = sentences[:4]

    bullets = "\n".join(f"- {s}" for s in selected)

    # citas (1–3)
    cited_pages = pages[:3]
    bullets += "\n\n" + "\n".join(f"(p. {p})" for p in cited_pages)

    bullets = re.sub(r"--- Página \d+ ---", "", bullets)
    bullets = re.sub(r"-\s*\n+", "", bullets)
    bullets = re.sub(r"\n{3,}", "\n\n", bullets)

    return bullets


def answer_factual(context: dict):
    text = context["context"]
    text = re.sub(r"--- Página \d+ ---", "", text)

    sentences = re.split(r"(?<=[.!?])\s+", text)
    for s in sentences:
        if len(s.strip()) > 80:
            return s.strip()

    return sentences[0].strip()


def handle_query(query: str):
    tool = detect_tool(query)
    doc = is_document_query(query)

    if tool and doc:
        rag = handle_rag(query)

        context_text = ""
        if isinstance(rag.get("answer"), str):
            context_text = rag["answer"]

        tool_call = call_tool(tool, query, context_text)

        return {
            "route": "BOTH",
            "rag": rag,
            "tool": tool_call,
        }

    if tool and not doc:
        return call_tool(tool, query)

    if doc:
        return handle_rag(query)

    return {
        "route": "NONE",
        "answer": "La información no aparece en el documento ni requiere herramientas externas.",
    }
