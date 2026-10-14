import json
import asyncio
import logging
from client.rag.index_pdf import load_pdf
from client.llm.mistral import call_mistral
from client.utils.settings import VECTORSTORE_PATH

# Configuración de ruta del perfil
PROFILER_PATH = VECTORSTORE_PATH.parent / "pdf_profile.json"
logger = logging.getLogger(__name__)

def get_cached_profile():
    """
    Lee el perfil guardado en disco. 
    Esta es la función que llama el Router para saber qué puede hacer el RAG.
    """
    try:
        if PROFILER_PATH.exists():
            with open(PROFILER_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Error al leer el perfil caché: {e}")
    
    # Perfil genérico de emergencia para que el sistema no se detenga
    return {
        "identidad": "Documento técnico",
        "capacidades_rag": ["información técnica general"],
        "fronteras_negativas": ["datos en tiempo real"],
        "metricas": "No detectadas",
        "instruccion_router": "Usa RAG si la pregunta es sobre el contenido del manual."
    }

async def generate_pdf_profile():
    """
    Analiza el PDF dinámicamente y genera el mapa de capacidades JSON.
    """
    docs = load_pdf()
    if not docs:
        print("DEBUG: ❌ No se pudieron cargar documentos para el profiling.")
        return

    # 1. Muestreo dinámico (Agnóstico al tamaño del PDF)
    total_pages = len(docs)
    sample_indices = sorted(list(set([
        0, 1,                    # Inicio / Índice
        total_pages // 2,        # Mitad
        max(0, total_pages - 1)  # Final / Glosario
    ])))
    
    extracto = []
    for i in sample_indices:
        if i < total_pages:
            extracto.append(f"[PÁGINA {i+1}]:\n{docs[i].page_content}")

    contexto_analisis = "\n\n".join(extracto)

    # 2. Prompt Meta-Analista
    prompt = f"""
    [INST] <<SYS>>
    Eres un Analista de Capacidades RAG. Tu tarea es mapear un documento desconocido.
    <</SYS>>
    Analiza estos fragmentos del documento para definir su identidad y límites:
    {contexto_analisis[:7000]}

    Genera ESTRICTAMENTE un JSON con esta estructura:
    {{
      "identidad": "Tema principal",
      "capacidades_rag": ["5 temas que SÍ trata"],
      "fronteras_negativas": ["5 temas que NO trata pero son similares"],
      "metricas": "¿Contiene tablas o porcentajes?",
      "instruccion_router": "Regla para decidir RAG vs TOOL"
    }}
    [/INST]
    """

    try:
        response = await call_mistral(prompt)
        # Limpieza de JSON para evitar ruidos de Ollama
        start = response.find("{")
        end = response.rfind("}") + 1
        json_payload = response[start:end]
        
        # Validación de integridad
        data = json.loads(json_payload)

        with open(PROFILER_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            
        print(f"DEBUG: ✅ Auto-Profiling finalizado: {data.get('identidad')}")
    except Exception as e:
        print(f"DEBUG: ❌ Error en Auto-Profiling: {e}")