import re
import time
import requests

from client.rag.retrieval import retrieve_chunks, build_hierarchical_context
from client.utils.settings import MCP_URL


def base_response():
    return {
        "route": None,
        "answer": None,
        "citations": [],
        "tool_calls": [],
        "debug": {},
    }


# -------------------- TOOL HELPERS --------------------


def format_tool_answer(tool_call: dict) -> str:
    if not tool_call.get("result"):
        return "No se pudo obtener respuesta de la herramienta."

    result = tool_call["result"]

    if tool_call["tool"] == "market_status":
        state = "abierto" if result.get("is_open") else "cerrado"
        return f"El mercado '{result.get('market')}' está {state} (a fecha {result.get('as_of')})."

    if tool_call["tool"] == "fx_rate":
        return f"El tipo de cambio {result.get('base')}/{result.get('quote')} es {result.get('rate')} (a fecha {result.get('as_of')})."

    return str(result)


def call_tool(tool: str, args: dict):
    start = time.time()
    try:
        resp = requests.post(f"{MCP_URL}/call/{tool}", json=args, timeout=10)
        payload = resp.json()
        result = payload.get("result")
        ok = payload.get("ok", False)
    except Exception as e:
        result = {"error": str(e)}
        ok = False

    return {
        "tool": tool,
        "args": args,
        "ok": ok,
        "result": result,
        "duration_ms": int((time.time() - start) * 1000),
    }


def get_target_currency(query: str, default=None):
    """
    Extrae la moneda objetivo de la query: 'a USD', 'to JPY', etc.
    Si no encuentra, devuelve default o None
    """
    match = re.search(r"\b(?:to|a|en)\s+([A-Z]{3})\b", query, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    return default


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


def extract_fx_args(query: str):
    candidates = re.findall(r"\b[A-Z]{3}\b", query.upper())
    base = candidates[0] if len(candidates) > 0 else "EUR"
    quote = candidates[1] if len(candidates) > 1 else "USD"
    return {"base": base, "quote": quote}


# -------------------- DOCUMENT HELPERS --------------------


def is_document_query(query: str):
    q = query.lower()
    keywords = [
        "documento",
        "pdf",
        "según",
        "segun",
        "qué es",
        "que es",
        "cual es",
        "cuál es",
        "explica",
        "describe",
        "notificación",
        "notificacion",
        "resumen",
        "resume",
        "guia",
        "guía",
    ]
    return any(k in q for k in keywords)


def extract_amount_from_text(text: str):
    """
    Extrae la cifra monetaria más relevante del texto (prioriza millones/miles).
    """
    money_pattern = r"([\d\.,]+)\s*(m|millones|mm|bn)?\s*(€|eur|usd|\$)?"
    matches = re.findall(money_pattern, text.lower())
    candidates = []

    for value, scale, currency in matches:
        try:
            number = float(value.replace(".", "").replace(",", "."))
        except ValueError:
            continue
        multiplier = 1
        if scale in ("m", "millones"):
            multiplier = 1_000_000
        elif scale in ("mm", "bn"):
            multiplier = 1_000_000_000
        candidates.append(number * multiplier)

    return max(candidates) if candidates else None


def handle_rag(query: str):
    docs, _ = retrieve_chunks(query)
    context = build_hierarchical_context(docs)

    if not docs:
        return {
            "answer": "La información no aparece en el documento.",
            "citations": [],
            "context_text": "",
        }

    # 🚀 Construimos la respuesta limpia
    def clean_text(text: str) -> str:
        # unir saltos de línea simples en espacio
        text = re.sub(r"\n+", " ", text)
        # quitar bullets y caracteres raros
        text = re.sub(r"[◼\*\-]+", "", text)
        # limpiar espacios múltiples
        text = re.sub(r"\s{2,}", " ", text)
        return text.strip()

    # elegimos entre resumen o respuesta factual
    if "resumen" in query.lower() or "resume" in query.lower():
        answer = summarize(context, query)
    else:
        # tomamos los chunks, limpiamos y concatenamos
        answer_texts = [clean_text(doc.page_content) for doc, _ in docs]
        # tomamos máximo 3 chunks para no saturar
        answer = " ".join(answer_texts[:3])

    # construimos citations (máx 3)
    seen = set()
    citations = []
    for doc, _ in docs:
        cid = doc.metadata.get("chunk_id")
        if cid in seen:
            continue
        seen.add(cid)
        citations.append(
            {
                "page": doc.metadata["page"],
                "chunk_id": cid,
                "text": doc.page_content[:500],  # puedes dejar más si quieres
            }
        )
        if len(citations) >= 3:
            break

    return {
        "answer": answer,
        "citations": citations,
        "context_text": context["context"],
    }


def summarize(context: dict, query: str):
    text = context["context"]
    pages = context["pages"]
    keywords = set(w.lower() for w in re.findall(r"\w+", query) if len(w) > 4)
    sentences = re.split(r"(?<=[.!?])\s+", text)

    scored = []
    for s in sentences:
        s_clean = s.strip()
        if 60 <= len(s_clean) <= 300:
            score = sum(1 for kw in keywords if kw in s_clean.lower())
            if score > 0:
                scored.append((score, s_clean))
    scored.sort(key=lambda x: x[0], reverse=True)
    selected = [s for _, s in scored[:6]] or sentences[:4]
    bullets = "\n".join(f"- {s}" for s in selected)
    bullets += "\n\n" + "\n".join(f"(p. {p})" for p in pages[:3])
    bullets = re.sub(r"--- Página \d+ ---", "", bullets)
    bullets = re.sub(r"-\s*\n+", "", bullets)
    bullets = re.sub(r"\n{3,}", "\n\n", bullets)
    return bullets


def answer_factual(context: dict):
    text = re.sub(r"--- Página \d+ ---", "", context["context"])

    # unir saltos de línea que no sean dobles
    text = re.sub(r"\n+", " ", text)

    # eliminar bullets y caracteres extraños
    text = re.sub(r"[◼\*\-]+", "", text)

    # separar en oraciones
    sentences = re.split(r"(?<=[.!?])\s+", text)

    for s in sentences:
        s_clean = s.strip()
        if len(s_clean) < 40:
            continue
        if "........" in s_clean:
            continue
        if s_clean.isupper():
            continue
        if re.match(r"^[A-Z\s]{10,}$", s_clean):
            continue
        return s_clean

    return sentences[0].strip() if sentences else ""


# -------------------- RESPONSE BUILDERS --------------------


def build_combined_answer(query: str, rag: dict, tool_call: dict) -> str:
    """
    Construye la respuesta final para BOTH (RAG + Tool), flexible para cualquier moneda y cifra.
    """
    if not tool_call or not tool_call.get("result"):
        return "Según el documento, no se pudo obtener el tipo de cambio."

    rate = tool_call["result"].get("rate")
    if rate is None:
        return "Según el documento, no se pudo obtener el tipo de cambio."

    base = tool_call["result"].get("base", "EUR")
    quote = tool_call["result"].get("quote", "USD")

    context_text = rag.get("context_text") or " ".join(
        c["text"] for c in rag.get("citations", [])
    )
    amount = extract_amount_from_text(context_text)
    if amount is None:
        return "No se pudo extraer una cifra del documento."

    converted = round(amount * rate, 2)
    page = rag["citations"][0]["page"] if rag.get("citations") else "N/A"
    amount_text = (
        rag["citations"][0]["text"].strip().split("\n")[0]
        if rag.get("citations")
        else "la cifra"
    )

    return f"Según el documento (p. {page}), el valor extraído es {amount:,.0f} {base}.\nAplicando el tipo de cambio {base}/{quote} ({rate}), el valor convertido es {converted:,.0f} {quote}.\n(Referencia: {amount_text[:100]}...)"


def is_ambiguous(query: str) -> bool:
    """
    Si es una query de conversión pero no detecta moneda explícita -> AMBIGUOUS
    """
    q = query.lower()
    if "convierte" in q and get_target_currency(query) is None:
        return True
    if "resumen" in q and not is_document_query(query):
        return True
    return False


# -------------------- MAIN HANDLER --------------------


def handle_query(query: str):
    resp = base_response()
    tool = detect_tool(query)
    doc = is_document_query(query)
    target_currency = get_target_currency(query)  # moneda objetivo

    resp["debug"]["tool_detected"] = tool
    resp["debug"]["doc_query"] = doc
    resp["debug"]["target_currency"] = target_currency

    # AMBIGUOUS
    if is_ambiguous(query):
        resp["route"] = "AMBIGUOUS"
        resp["answer"] = (
            "La pregunta es ambigua.\n¿Quieres usar información del documento o una herramienta externa?"
        )
        return resp

    # BOTH: documento + moneda objetivo
    if doc and target_currency is not None:
        resp["route"] = "BOTH"
        rag = handle_rag(query)
        resp["citations"] = rag["citations"]

        # usamos EUR como base por defecto
        tool_args = {"base": "EUR", "quote": target_currency}
        tool_call = call_tool("fx_rate", tool_args)
        resp["tool_calls"].append(tool_call)

        resp["answer"] = build_combined_answer(query, rag, tool_call)
        return resp

    # TOOL solo
    if tool:
        resp["route"] = "TOOL"
        args = (
            extract_fx_args(query) if tool == "fx_rate" else extract_market_args(query)
        )
        tool_call = call_tool(tool, args)
        resp["tool_calls"].append(tool_call)
        resp["answer"] = format_tool_answer(tool_call)
        return resp

    # RAG solo
    if doc:
        resp["route"] = "RAG"
        rag = handle_rag(query)
        resp["answer"] = rag["answer"]
        resp["citations"] = rag["citations"]
        return resp

    # NONE
    resp["route"] = "NONE"
    resp["answer"] = (
        "La información no aparece en el documento ni puede obtenerse mediante herramientas externas."
    )
    return resp
