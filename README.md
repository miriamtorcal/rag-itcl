Asistente conversacional diseñado para responder preguntas sobre un PDF de referencia con citación de páginas y fragmentos y posibilidad de llamada a herramientas externas (MCP) vía SSE.
El sistema combina RAG jerárquico, fallback léxico, logs trazables, y arquitectura modular para asegurar correctitud, reproducibilidad y mantenibilidad.
Tabla de contenidos
Estructura de carpetas
Requisitos
Ejecución
Chunking y embeddings
Recuperación de contexto jerárquico
Fallback léxico
Logs y trazabilidad
Tests
Notas
Estructura de carpetas
itcl_rag_mcp/
├─ client/
│  ├─ app.py             # FastAPI / Streamlit
│  ├─ router.py          # Orquestador RAG vs Tool
│  ├─ rag/
│  │  ├─ index_pdf.py    # Indexa PDF y chunks
│  │  ├─ retrieval.py    # Recupera contexto jerárquico y fallback
│  │  └─ embeddings.py   # Generación de embeddings
│  └─ utils/
│     ├─ logger.py       # Logs JSON trazables
│     └─ settings.py     # Configuraciones (paths, thresholds, etc.)
├─ mcp_server/
│  ├─ server.py          # Exposición de tools vía SSE / endpoints
│  ├─ tools/
│  │  ├─ fx_rate.py      # Mock determinista de tool
│  │  └─ market_status.py# Mock determinista de tool
│  └─ utils.py           # Helpers para logs y herramientas
├─ data/
│  ├─ pdf_example.pdf    # PDF de referencia
│  └─ vector/            # VectorStore persistente
├─ tests/
│  ├─ test_rag.py
│  ├─ test_tools.py
│  └─ test_router.py
├─ docker-compose.yml
├─ requirements.txt / poetry.lock
└─ README.md
Requisitos
Python ≥ 3.10
Docker + Docker Compose
Librerías: langchain, sentence-transformers, Chroma, FastAPI, Streamlit/Gradio
Variables de entorno configuradas según .env.example
Ejecución
Construir y levantar contenedores:
docker compose up --build
Abrir la UI:
http://localhost:8501
Para reindexar el PDF:
python -m client.rag.index_pdf --reindex
Chunking y embeddings
Se utiliza RecursiveCharacterTextSplitter para generar chunks de ~800 caracteres con solapamiento de 150.
Cada chunk contiene metadatos: page, chunk_id, source.
Los embeddings se generan en embeddings.py usando sentence-transformers (all-MiniLM-L6-v2), y se almacenan en data/vector/.
El índice se persiste con Chroma local para reutilización sin recalcular embeddings.
Recuperación de contexto jerárquico
retrieve_chunks(query) realiza búsqueda semántica con similarity_search_with_score.
Se filtra según SCORE_THRESHOLD para asegurar solo resultados relevantes.
build_hierarchical_context(results) reconstruye el contexto agrupando por página y limitando a MAX_CHUNKS_PER_PAGE.
Devuelve contexto concatenado, páginas citadas y metadatos de chunks.
Fallback léxico
Si ningún resultado supera el threshold semántico, se activa keyword_fallback_retrieval(query, docs).
Extrae keywords significativas de la query (≥4 caracteres) y busca coincidencias textuales en los chunks.
Permite recuperar información que la búsqueda semántica no encuentra pero sí existe en el PDF.
Logs y trazabilidad
Todas las consultas se registran en client/utils/logger.py.
Campos logueados:
{
  "timestamp": "ISO UTC",
  "query": "texto de consulta",
  "route": "RAG | TOOL | BOTH",
  "chunks_retrieved": [{"chunk_id": "...", "page": 0, "score": 0.123}],
  "used_lexical_fallback": true|false
}
Logs en pantalla y archivo JSON, trazables para depuración.
Tests
Tests mínimos implementados en tests/:
test_rag.py: retrieval y build_hierarchical_context
test_tools.py: mocks de herramientas MCP
test_router.py: enrutado entre RAG y tools
Cobertura mínima: 3 casos de prueba esenciales por flujo.
Notas
El PDF de ejemplo es solo referencia; el sistema permite cualquier PDF con texto seleccionable.
MCP server y cliente son independientes; se comunican vía SSE y endpoints REST.
Faltan ajustes finales de UI, que se integrarán sobre la arquitectura existente.
Documentación técnica completa y README permiten reproducibilidad inmediata con Docker Compose.