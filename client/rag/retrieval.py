import re
from client.rag.index_pdf import load_index
from client.utils.logger import log_event
from client.utils.settings import MAX_PAGES

def retrieve_chunks(query, k=15, max_per_page=3):
    vectorstore = load_index()
    match = re.search(r"p[aá]g(?:ina)?\.?\s+(\d+)", query, re.IGNORECASE)
    target_page = int(match.group(1)) if match else None

    # Búsqueda normal
    results = vectorstore.similarity_search_with_score(query, k=5)
    forced_docs = []

    if target_page is not None:
        print(f"DEBUG: 🚨 Forzando ventana alrededor de Página {target_page}", flush=True)
        # Definimos el rango: [objetivo - 2, objetivo + 2]
        window = range(target_page - 2, target_page + 3)
        
        for p in window:
            # Buscamos por el número de página (intentamos int y str)
            for val in [p, str(p)]:
                found = vectorstore.similarity_search(query, k=5, filter={"page": val})
                if found:
                    forced_docs.extend(found)
        
        # SI HAY PÁGINA OBJETIVO: Ignoramos la búsqueda vectorial general 
        # para evitar que el índice (pág 4) ensucie el contexto.
        if forced_docs:
            results = [(doc, 0.0) for doc in forced_docs]
    
    # Filtrado final
    filtered = []
    per_page_count = {}

    for doc, score in results:
        page = doc.metadata.get("page")
        if page is None: continue
        
        # Si pedimos una página y esta NO está en el rango +-2, la descartamos
        if target_page and not (target_page - 2 <= int(page) <= target_page + 2):
            continue

        per_page_count.setdefault(page, 0)
        limit = 10 if (target_page and int(page) == target_page) else max_per_page

        if per_page_count[page] < limit:
            per_page_count[page] += 1
            filtered.append((doc, score))

    return filtered, {"pages": list(per_page_count.keys())}


def build_hierarchical_context(results, max_chunks_per_page=3):
    """
    Construye el contexto agrupando por páginas y respetando el orden.
    """
    pages = {}
    for doc, score in results:
        page = doc.metadata.get("page")
        pages.setdefault(page, [])
        if doc.page_content not in pages[page]:
            pages[page].append(doc.page_content)

    context_blocks = []
    # Ordenamos las páginas para que el modelo lea en orden lógico
    sorted_pages = sorted(pages.keys())
    
    for page in sorted_pages:
        # Si la página tiene muchos chunks, es que ha sido forzada (probablemente una tabla)
        # Usamos ternario para decidir si mostramos más contenido de esa página
        limit = 10 if len(pages[page]) > 3 else max_chunks_per_page
        texts = pages[page][:limit]
        
        context_blocks.append(f"\n--- Página {page} ---\n" + "\n".join(texts))

    return {
        "context": "\n\n".join(context_blocks),
        "pages": sorted_pages,
    }


def _normalize_block(text: str) -> str:
    """Normaliza un bloque de PDF para deduplicación."""
    text = text.lower()
    text = re.sub(r"[◼▪•■]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def keyword_fallback_retrieval(query: str, docs, max_results=5):
    keywords = [w.lower() for w in re.findall(r"\w+", query) if len(w) > 3]
    matched = []
    for doc, score in docs:
        content = doc.page_content.lower()
        if any(kw in content for kw in keywords):
            matched.append((doc, score))
    return matched[:max_results]