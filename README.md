# Asistente Conversacional con RAG Jerárquico y Soporte MCP

Asistente conversacional diseñado para responder preguntas sobre un PDF de referencia con citación de páginas y soporte para herramientas externas vía **MCP (Model Context Protocol)** mediante **SSE** para la ejecución de tools.

El sistema combina:

- ✅ RAG jerárquico con citación por página  
- ✅ Fallback léxico controlado  
- ✅ Orquestador RAG / TOOL / BOTH / NONE  
- ✅ Tools deterministas vía MCP  
- ✅ Logs estructurados y trazables  
- ✅ Arquitectura modular y reproducible con Docker  

---

## Tabla de Contenidos

- [Arquitectura General](#arquitectura-general)  
- [Estructura del Proyecto](#estructura-del-proyecto)  
- [Requisitos](#requisitos)  
- [Configuración](#configuración)  
- [Ejecución con Docker](#ejecución-con-docker)  
- [Chunking y Embeddings](#chunking-y-embeddings)  
- [Recuperación Jerárquica](#recuperación-jerárquica)  
- [Fallback Léxico](#fallback-léxico)  
- [Estrategia de Enrutado](#estrategia-de-enrutado)  
- [Logs y Trazabilidad](#logs-y-trazabilidad)  
- [Limitaciones y Decisiones de Diseño](#limitaciones-y-decisiones-de-diseño)  
- [Tests](#tests)  
- [Resultados Probados](#resultados)  
- [Conclusión](#conclusión)
---

## Arquitectura General

El sistema está dividido en dos servicios independientes:

### 1️⃣ Client (Streamlit + RAG + Router)

**Responsabilidades:**

- Indexación del PDF  
- Generación de embeddings  
- Recuperación semántica  
- Fallback léxico  
- Orquestación RAG / TOOL / BOTH / NONE  
- Cálculo en conversiones (ej. cifras + tipo de cambio)  
- Logging estructurado  
- Interfaz de usuario  

**Incluye:**

- Dockerfile propio  
- `requirements.txt` propio  

### 2️⃣ MCP Server (FastAPI)

**Responsabilidades:**

- Exposición de herramientas externas  
- Ejecución de tools deterministas vía SSE  
- Registro independiente de logs  

**Incluye:**

- Dockerfile propio  
- `requirements.txt` propio  

**Notas sobre MCP y SSE:**

- Las tool calls se realizan vía **SSE**, garantizando comunicación asíncrona y trazable.  
- El cliente obtiene la lista de herramientas mediante endpoint REST (`GET /tools`) al iniciar, evitando hardcodear nombres en el cliente.  
- La ejecución de cada tool se solicita vía POST (`/call/<tool>`), recibiendo resultados de manera trazable.  

```text
Usuario
   |
Client (UI + Router + RAG)
   |      
   +--------+
   |        |
VectorStore  MCP Server (Tools SSE)
(Chroma)        |
            Tools Mock
           fx_rate / market_status
```
---

## Estructura del Proyecto

```text
rag_itcl/
├─ client/
│  ├─ Dockerfile
│  ├─ requirements.txt
│  ├─ app.py
│  ├─ router.py
│  ├─ mcp/
│  │  └─ discovery.py
│  ├─ rag/
│  │  ├─ index_pdf.py
│  │  ├─ retrieval.py
│  │  └─ embeddings.py
│  └─ utils/
│     ├─ logger.py
│     └─ settings.py
│
├─ mcp_server/
│  ├─ Dockerfile
│  ├─ requirements.txt
│  ├─ server.py
│  ├─ tools/
│  │  ├─ fx_rate.py
│  │  └─ market_status.py
│  ├─ logger.py
│  └─ utils.py
│
├─ data/
│  ├─ pdf_example.pdf
│  └─ vector/
│
├─ tests/
│  ├─ test_rag.py
│  ├─ test_tools.py
│  └─ test_router.py
├─ logs/
│  └─ app.log
├─ docker-compose.yml
├─ .env
└─ README.md
```
---

## Requisitos
**Docker**

**Docker Compose**

**Python ≥ 3.12 (solo si se ejecuta sin Docker)**

### Dependencias principales:

```bash
pip install langchain
pip install sentence-transformers
pip install chromadb
pip install fastapi
pip install streamlit
```

Cada servicio tiene su propio entorno aislado vía Docker.

---
## Configuración

Variables de entorno en .env:

```text
FILE_PATH="guia_incibe_gestion_ciberdelincuentes.pdf"
VECTORSTORE_PATH="vector"
LOG_DIR="logs"
LOG_FILE="app.log"
EMBEDDING_MODEL="sentence-transformers/all-MiniLM-L6-v2"
SCORE_THRESHOLD=0.7
MAX_PAGES=3
MCP_URL="http://mcp_server:8081"
```


Las rutas se resuelven automáticamente dentro del volumen data/.

---
## Ejecución con Docker

Construcción y arranque:
```bash
docker compose up --build
```

Esto levanta:

client → http://localhost:8501

mcp_server → http://localhost:8081

**Reindexar manualmente:**
```bash
docker compose exec client python -m client.rag.index_pdf --reindex
```
El índice se guarda en `data/vector/`.

---

## Chunking y Embeddings

- **Splitter:** `RecursiveCharacterTextSplitter`  
- **Tamaño:** ~800 caracteres  
- **Solapamiento:** 150 caracteres  
- **Metadatos por chunk:** `page`, `chunk_id`, `source`  
- **Embeddings:** `sentence-transformers/all-MiniLM-L6-v2`  
- **VectorStore:** Chroma persistente  
- Evita recalcular embeddings si ya existen  

---

## Recuperación Jerárquica

**Flujo de trabajo:**

```python
similarity_search_with_score(query)
# Filtrado por SCORE_THRESHOLD
# Agrupación por página
# Reconstrucción limitada por MAX_PAGES
```

**Ventajas:**

- Coherencia contextual  
- No se inyecta el PDF completo  
- Citación clara por página  

---

## Fallback Léxico

- Activado si ningún chunk supera el umbral semántico  
- Búsqueda por keywords significativas  
- Resultados se registran en logs: `"used_lexical_fallback": true`  

---

## Estrategia de Enrutado

El router clasifica cada consulta en:

| Consulta                                   | Ruta       |
|-------------------------------------------|-----------|
| ¿Qué es el Producto Interior Bruto?       | RAG       |
| ¿Cuándo bajó el USD?                       | AMBIGUOUS |
| Convierte el Producto Interior Bruto a USD| BOTH      |
| ¿Capital de Marte?                         | NONE      |

---

## Logs y Trazabilidad

**Formato JSON de ejemplo:**

```json
{
  "timestamp": "ISO UTC",
  "query": "...",
  "route": "RAG | TOOL | BOTH | NONE | AMBIGUOUS",
  "chunks_retrieved": [{"chunk_id": "...", "page": 3, "score": 0.82}],
  "tool_calls": [{"name": "fx_rate", "duration_ms": 31}],
  "used_lexical_fallback": false
}
```
- **Ubicación de logs:** `logs/app.log`  

**Garantiza:**

- Reproducibilidad  
- Observabilidad  
- Auditoría de decisiones  

---

## Limitaciones y Decisiones de Diseño

- **PDF con texto seleccionable:** No se implementa OCR. PDFs escaneados no serán indexados.  
- **Extracción numérica:** Se priorizan magnitudes grandes y se valida proximidad semántica.  
- **Conversión desacoplada (RAG + Tool):** RAG obtiene cifra y moneda, tool aporta tipo de cambio.  
- **Ambigüedad en símbolos monetarios:** $ → USD, € → EUR. Se recomienda usar códigos ISO.  
- **Recuperación limitada:** Solo se reconstruyen hasta `MAX_PAGES` páginas relevantes.  
- **Tools deterministas:** No dependen de internet; garantizan ejecución offline completa.  
- **Acrónimos aislados:** Consultas muy cortas con acrónimos (ej. P.I.B. o PIB) pueden fallar. Se aplica query expansion: P.I.B. → Producto Interior Bruto.

---

## Tests

- **Ubicación:** `tests/`  
- **Cubren:**  
  - Recuperación con citación  
  - Activación de fallback  
  - Enrutado correcto  
  - Ejecución de tools  
  - Caso NONE

---
## Resultados Probados

A continuación se muestran consultas reales ejecutadas sobre el sistema antes de la entrega, indicando la ruta de resolución activada y la fuente utilizada.

### 🔎 Casos RAG (solo PDF)

| Consulta | Resultado Resumido | Ruta |
|----------|-------------------|------|
| ¿Qué es la notificación de incidentes? | Definición de notificación inicial e intermedia, con referencia a la ventana temporal y nivel de impacto | RAG |
| Resumen de la notificación de incidentes | Carácter potestativo y voluntario; información a notificar en la notificación final | RAG |

**Fuente:** PDF indexado (citaciones por página incluidas en la respuesta).

---

### 🔧 Casos BOTH (PDF + Tool)

| Consulta | Resultado Resumido | Ruta |
|----------|-------------------|------|
| Convierte el Producto Interior Bruto del documento a USD | Extrae 1,163,663,000,000 EUR del PDF y aplica tipo de cambio EUR/USD | BOTH |
| Convierte el Producto Interior Bruto del documento a JPY | Extrae valor del PDF y aplica tipo de cambio EUR/JPY | BOTH |

**Flujo aplicado:**

1. RAG recupera la cifra del documento  
2. Tool `fx_rate` devuelve el tipo de cambio  
3. El client calcula la conversión final  
4. Se registra trazabilidad en logs  

---

### 🌐 Casos TOOL (solo herramientas externas)

| Consulta | Resultado | Ruta |
|----------|----------|------|
| ¿Está cerrado Nasdaq? | Estado del mercado obtenido vía `market_status` | TOOL |
| ¿Está abierto el mercado de Tokio? | Estado del mercado obtenido vía `market_status` | TOOL |
| ¿Cuánto vale el PIB en USD? | Tipo de cambio obtenido vía `fx_rate` | TOOL |

**Nota:** Las tools son deterministas y no dependen de conexión a internet.

---

### 🚫 Casos NONE (fuera de alcance)

| Consulta | Resultado | Ruta |
|----------|----------|------|
| ¿Qué hora es? | No disponible en PDF ni tools | NONE |
| ¿Ha llovido hoy? | No disponible en PDF ni tools | NONE |

El sistema evita generar respuestas inventadas cuando no existe fuente válida.

---

## Consideraciones sobre Ambigüedad

Existen consultas que pueden resultar ambiguas debido a:

- Falta de contexto suficiente (ej. "Convierte dinero a USD")
- Acrónimos aislados (ej. "PIB")
- Uso implícito de moneda base no especificada

En estos casos el router puede clasificar como:

- `AMBIGUOUS`
- `TOOL`
- `BOTH`

dependiendo del análisis heurístico implementado.

---

## Garantías de Reproducibilidad

Todos los resultados anteriores se obtienen ejecutando:

```bash
docker compose up --build
```
---
## Conclusión

El sistema implementa una arquitectura modular, trazable y reproducible, basada en:

- RAG jerárquico con citación  
- Orquestación híbrida RAG + Tools  
- Logging estructurado  
- Separación clara client / mcp_server  
- Docker Compose reproducible  

**Se priorizan:**

- Correctitud  
- Transparencia  
- Reproducibilidad  
- Mantenibilidad
