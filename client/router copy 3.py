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


def format_tool_answer(tool_call: dict) -> str:
    if not tool_call.get("result"):
        return "No se pudo obtener respuesta de la herramienta."

    result = tool_call["result"]

    if tool_call["tool"] == "market_status":
        state = "abierto" if result.get("is_open") else "cerrado"
        return (
            f"El mercado '{result.get('market')}' está {state} "
            f"(a fecha {result.get('as_of')})."
        )

    if tool_call["tool"] == "fx_rate":
        return (
            f"El tipo de cambio {result.get('base')}/{result.get('quote')} "
            f"es {result.get('rate')} (a fecha {result.get('as_of')})."
        )

    return str(result)


def get_target_currency(query: str, default="USD"):
    match = re.search(r"\b(to|a|en)\s+([A-Z]{3})\b", query, re.IGNORECASE)
    if match:
        return match.group(2).upper()
    return default


def is_ambiguous(query: str) -> bool:
    q = query.lower()

    # extraemos si hay divisas
    fx_args = extract_fx_args(query)
    base = fx_args.get("base")
    quote = fx_args.get("quote")

    # si convierte pero no detectamos moneda -> ambiguo
    if "convierte" in q and (base is None or quote is None):
        return True

    if "resumen" in q and not is_document_query(query):
        return True

    return False


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

        total = number * multiplier
        candidates.append(total)

    # elegimos la cifra más grande (PIB suele serlo)
    return max(candidates) if candidates else None


def extract_fx_args(query: str):
    candidates = re.findall(r"\b[A-Z]{3}\b", query.upper())

    base = candidates[0] if len(candidates) > 0 else "EUR"
    quote = candidates[1] if len(candidates) > 1 else "USD"

    return {"base": base, "quote": quote}


def call_tool(tool: str, args: dict):
    start = time.time()

    try:
        resp = requests.post(f"{MCP_URL}/call/{tool}", json=args, timeout=10)
        payload = resp.json()
        ok = payload.get("ok", False)
        result = payload.get("result")
    except Exception as e:
        ok = False
        result = {"error": str(e)}

    return {
        "tool": tool,
        "args": args,
        "ok": ok,
        "result": result,
        "duration_ms": int((time.time() - start) * 1000),
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
            "resume",
        ]
    )


def handle_ambiguous(query: str):
    return {
        "route": "AMBIGUOUS",
        "answer": (
            "La pregunta es ambigua y puede resolverse de varias formas.\n"
            "¿Podrías concretar un poco más?\n"
            "- ¿Qué valor quieres convertir?\n"
            "- ¿A qué moneda?"
        ),
    }


def handle_rag(query: str):
    docs, meta = retrieve_chunks(query)
    context = build_hierarchical_context(docs)

    if not docs:
        return {
            "answer": "La información no aparece en el documento.",
            "citations": [],
            "context_text": "",
        }

    answer = (
        summarize(context, query)
        if "resumen" or "resume" in query.lower()
        else answer_factual(context)
    )

    seen = set()
    citations = []

    for doc, score in docs:
        cid = doc.metadata.get("chunk_id")
        if cid in seen:
            continue
        seen.add(cid)

        citations.append(
            {
                "page": doc.metadata["page"],
                "chunk_id": cid,
                "text": doc.page_content[:200],
            }
        )

        if len(citations) >= 3:
            break

    return {
        "answer": answer,
        "citations": citations,
        "context_text": context["context"],
    }


def build_combined_answer(query: str, rag: dict, tool_call: dict) -> str:
    """
    Construye la respuesta final para BOTH (RAG + Tool), flexible para cualquier moneda
    y cualquier cifra del documento.
    """
    if not tool_call or not tool_call.get("result"):
        return "Según el documento, no se pudo obtener el tipo de cambio."

    rate = tool_call["result"].get("rate")
    if rate is None:
        return "Según el documento, no se pudo obtener el tipo de cambio."

    base = tool_call["result"].get("base", "EUR")
    quote = tool_call["result"].get("quote", "USD")

    # Extraemos cantidad del contexto RAG
    context_text = rag.get("context_text") or " ".join(
        c["text"] for c in rag.get("citations", [])
    )
    amount = extract_amount_from_text(context_text)
    if amount is None:
        return "No se pudo extraer una cifra del documento."

    converted = round(amount * rate, 2)
    # Usamos la primera cita como referencia
    page = rag["citations"][0]["page"] if rag.get("citations") else "N/A"
    amount_text = (
        rag["citations"][0]["text"].strip().split("\n")[0]
        if rag.get("citations")
        else "la cifra"
    )

    return (
        f"Según el documento (p. {page}), el valor extraído es {amount:,.0f} {base}.\n"
        f"Aplicando el tipo de cambio {base}/{quote} ({rate}), el valor convertido es {converted:,.0f} {quote}.\n"
        f"(Referencia: {amount_text[:100]}...)"
    )


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
    resp = base_response()

    tool = detect_tool(query)
    doc = is_document_query(query)

    resp["debug"]["tool_detected"] = tool
    resp["debug"]["doc_query"] = doc

    # AMBIGUOUS (T6)
    if is_ambiguous(query):
        resp["route"] = "AMBIGUOUS"
        resp["answer"] = (
            "La pregunta es ambigua.\n"
            "¿Quieres usar información del documento o una herramienta externa?"
        )
        return resp

    # BOTH (T3)
    if tool and doc:
        resp["route"] = "BOTH"

        rag = handle_rag(query)
        resp["citations"] = rag["citations"]

        target_currency = get_target_currency(query, "USD")
        tool_args = {"base": "EUR", "quote": target_currency}
        tool_call = call_tool("fx_rate", tool_args)

        # forzamos que nunca sea None
        if tool_call is None:
            tool_call = {
                "result": {},
                "ok": False,
                "tool": "fx_rate",
                "args": tool_args,
                "duration_ms": 0,
            }

        resp["tool_calls"].append(tool_call)

        resp["answer"] = build_combined_answer(query, rag, tool_call)
        return resp

    # TOOL (T4)
    if tool:
        resp["route"] = "TOOL"
        args = (
            extract_fx_args(query) if tool == "fx_rate" else extract_market_args(query)
        )
        tool_call = call_tool(tool, args)
        resp["tool_calls"].append(tool_call)
        resp["answer"] = format_tool_answer(tool_call)
        return resp

    # RAG (T1, T2)
    if doc:
        resp["route"] = "RAG"
        rag = handle_rag(query)
        resp["answer"] = rag["answer"]
        resp["citations"] = rag["citations"]
        return resp

    # NONE (T5)
    resp["route"] = "NONE"
    resp["answer"] = (
        "La información no aparece en el documento "
        "ni puede obtenerse mediante herramientas externas."
    )
    return resp
