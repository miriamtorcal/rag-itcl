import httpx
import json
from client.utils.settings import OLLAMA_URL

async def call_mistral(prompt: str, is_json: bool = False) -> str:
    payload = {
        "model": "llama3.2",
        "prompt": prompt,
        "stream": False,
        "options": {
            "num_thread": 4,
            "num_ctx": 8192,
            "temperature": 0,
        },
    }
    if is_json:
        payload["format"] = "json"

    async with httpx.AsyncClient(timeout=300.0) as client:
        try:
            response = await client.post(OLLAMA_URL, json=payload)
            response.raise_for_status()
            return response.json()["response"].strip()
        except Exception as e:
            print(f"DEBUG: ❌ Error en call_mistral: {e}")
            return json.dumps({"error": str(e)}) if is_json else f"Error: {e}"

async def generate_answer(query: str, context: str) -> str:
    prompt = f"""
    [INST] <<SYS>>
    Eres un Agente Técnico Experto. Tu misión es generar respuestas claras, profesionales y con formato Markdown/LaTeX impecable.
    <</SYS>>

    ### 📥 CONTEXTO (PDF + TOOLS)
    {context}

    ### 🎨 REGLAS DE FORMATO (OBLIGATORIAS):
    1. **Fórmulas**: Usa SIEMPRE bloques de LaTeX centrados: $$ \\frac{{ \\text{{ Texto Arriba }} }}{{ \\text{{ Texto Abajo }} }} $$. 
    2. **Espaciado**: NUNCA pegues palabras dentro de una fórmula. Usa espacios claros.
    3. **Prohibición**: No uses el símbolo '#' dentro de las fórmulas. Escribe 'num.' o la palabra completa.
    4. **Tablas**: Si el contexto tiene umbrales o datos comparativos, preséntalos en una Tabla Markdown.
    5. **Títulos**: Usa ## para separar secciones.

    ### ❓ PREGUNTA DEL USUARIO:
    "{query}"

    RESPUESTA ESTRUCTURADA:
    [/INST]
    """
    return await call_mistral(prompt)