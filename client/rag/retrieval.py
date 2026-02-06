import re

from client.rag.index_pdf import load_index
from client.utils.settings import MAX_CHUNKS_PER_PAGE, SCORE_THRESHOLD
from client.utils.logger import log_event

def retrieve_chunks(query: str, k: int = 8):
    vectorstore = load_index()
    docs = vectorstore.similarity_search_with_score(query, k=k)

    filtered = [(doc, score) for doc, score in docs if score < SCORE_THRESHOLD]

    if filtered:
        filtered_sorted = sorted(filtered, key=lambda x: x[1])
        return filtered_sorted[:5], {
            "route": "RAG",
            "used_lexical_fallback": False
        }

    fallback = keyword_fallback_retrieval(query, docs)
    if fallback:
        return fallback, {
            "route": "RAG",
            "used_lexical_fallback": True
        }

    return [], {
            "route": "NONE",
            "used_lexical_fallback": False
        }


def build_hierarchical_context(results):
    pages = {}

    for doc, score in results:
        page = doc.metadata.get("page")
        if page not in pages:
            pages[page] = []
        pages[page].append(doc.page_content)

    context_blocks = []
    citations = []

    for page in sorted(pages.keys()):
        texts = pages[page][:MAX_CHUNKS_PER_PAGE]
        context_blocks.append(f"\n--- Página {page} ---\n" + "\n".join(texts))
        citations.append(page)

    return {
        "context": "\n\n".join(context_blocks),
        "pages": sorted(citations),
        "chunks": [
            {
                "page": doc.metadata.get("page"),
                "chunk_id": doc.metadata.get("chunk_id"),
                "score": score,
            }
            for doc, score in results
        ],
    }



def keyword_fallback_retrieval(query: str, docs, max_results=5):
    keywords = [w.lower() for w in re.findall(r"\w+", query) if len(w) > 3]

    matched = []

    for doc, score in docs:
        content = doc.page_content.lower()
        if any(kw in content for kw in keywords):
            matched.append((doc, score))

    return matched[:max_results]


if __name__ == "__main__":
    query = "notificación de incidentes"
    print(f"Query 1 -> {query}")
    results, decision = retrieve_chunks(query)
    data = build_hierarchical_context(results)
    log_event({
        "query": query,
        "route": decision["route"],
        "used_lexical_fallback": decision["used_lexical_fallback"],
        "num_chunks": len(data.get("chunks", [])),
        "chunks_retrieved": [
            {"chunk_id": c["chunk_id"], "page": c["page"]}
            for c in data.get("chunks")
        ]
    })

    print("PÁGINAS:", data["pages"])
    print("CONTEXTO:", data["context"][:500])



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
