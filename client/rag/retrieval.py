import re

from client.rag.index_pdf import load_index
from client.utils.logger import log_event
from client.utils.settings import (
    MAX_PAGES,
)


def retrieve_chunks(query, k=10, max_per_page=2):
    """
    Recupera chunks diversificados por página.
    """
    vectorstore = load_index()
    results = vectorstore.similarity_search_with_score(query, k=30)

    filtered = []
    per_page_count = {}

    for doc, score in results:
        page = doc.metadata.get("page")

        if page is None:
            continue

        per_page_count.setdefault(page, 0)

        # limitar chunks por página
        if per_page_count[page] >= max_per_page:
            continue

        per_page_count[page] += 1
        filtered.append((doc, score))

        if len(filtered) >= k:
            break

    return filtered, {
        "total_candidates": len(results),
        "returned": len(filtered),
        "pages": list(per_page_count.keys()),
    }


def _normalize_block(text: str) -> str:
    """
    Normaliza un bloque de PDF para deduplicación.
    """
    text = text.lower()
    text = re.sub(r"[◼▪•■]", "", text)  # quitar viñetas
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def build_hierarchical_context(results, max_chunks_per_page=2):
    pages = {}

    for doc, score in results:
        page = doc.metadata.get("page")
        pages.setdefault(page, [])

        # evita duplicados casi iguales
        if doc.page_content not in pages[page]:
            pages[page].append(doc.page_content)

    context_blocks = []
    citations = []

    for page in sorted(pages.keys())[:MAX_PAGES]:
        texts = pages[page][:max_chunks_per_page]
        context_blocks.append(f"\n--- Página {page} ---\n" + "\n".join(texts))
        citations.append(page)

    return {
        "context": "\n\n".join(context_blocks),
        "pages": citations,
    }


def keyword_fallback_retrieval(query: str, docs, max_results=5):
    keywords = [w.lower() for w in re.findall(r"\w+", query) if len(w) > 3]

    matched = []

    for doc, score in docs:
        content = doc.page_content.lower()
        if any(kw in content for kw in keywords):
            matched.append((doc, score))

    return matched[:max_results]


# if __name__ == "__main__":
#     query = "notificación de incidentes"
#     print(f"Query 1 -> {query}")
#     results, decision = retrieve_chunks(query)
#     data = build_hierarchical_context(results)
#     log_event({
#         "query": query,
#         "route": decision["route"],
#         "used_lexical_fallback": decision["used_lexical_fallback"],
#         "num_chunks": len(data.get("chunks", [])),
#         "chunks_retrieved": [
#             {"chunk_id": c["chunk_id"], "page": c["page"]}
#             for c in data.get("chunks")
#         ]
#     })

#     print("PÁGINAS:", data["pages"])
#     print("CONTEXTO:", data["context"][:500])


# query = "el vino en la ribera del duero"
# print(f"Query 2 -> {query}")
# results = retrieve_chunks(query)
# data = build_hierarchical_context(results)

# print("PÁGINAS:", data["pages"])
# print("CONTEXTO:", data["context"][:500])

# query = "ataque POODLE"
# print(f"Query 3 -> {query}")
# results = retrieve_chunks(query)
# data = build_hierarchical_context(results)

# print("PÁGINAS:", data["pages"])
# print("CONTEXTO:", data["context"][:500])

# query = "que es un ataque POODLE"
# print(f"Query 4 -> {query}")
# results = retrieve_chunks(query)
# data = build_hierarchical_context(results)

# print("PÁGINAS:", data["pages"])
# print("CONTEXTO:", data["context"][:500])
