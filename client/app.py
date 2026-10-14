import asyncio
import re
import streamlit as st
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client

# Importaciones de tu lógica interna
from client.rag.index_pdf import build_index
from client.rag.profiler import generate_pdf_profile
from client.router import handle_query
from client.utils.settings import MCP_URL
from client.data_mcp.discovery import discover_tools

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Asistente RAG Jerárquico + MCP",
    layout="wide",
    page_icon="🛡️"
)

# --- 1. GESTIÓN DE ESTADO E INICIALIZACIÓN ---
@st.cache_resource
def initialize_system():
    """Inicializa el índice y descubre herramientas una sola vez."""
    status = {"mcp": False, "rag": False, "tools": [], "error": None}
    try:
        # A. Descubrimiento de Tools (Requisito 4.3)
        tools = asyncio.run(asyncio.wait_for(discover_tools(), timeout=10.0))
        status["mcp"] = True
        status["tools"] = tools
        
        # B. RAG Jerárquico (Requisito 4.2)
        build_index()  # Crea el VectorStore
        asyncio.run(generate_pdf_profile()) # Genera el resumen para el router
        status["rag"] = True
    except Exception as e:
        status["error"] = str(e)
    return status

# Sidebar de Estado y Debug
with st.sidebar:
    st.header("⚙️ Panel de Control")
    debug_mode = st.checkbox("Activar Modo Depuración", value=True)
    
    health = initialize_system()
    
    if health["mcp"]:
        st.success("✅ MCP Server: Conectado")
        with st.expander("Ver Catálogo de Tools"):
            for t in health["tools"]:
                st.caption(f"**{t['name']}**: {t['description']}")
    else:
        st.error("❌ MCP Server: Error")
        
    if health["rag"]:
        st.success("✅ RAG Index: Listo")
    
    if st.button("🔄 Reindexar PDF", help="Cumple requisito 4.1"):
        with st.spinner("Reindexando..."):
            build_index(force=True)
            st.rerun()

# --- 2. HELPERS TÉCNICOS ---

def clean_llm_latex(text):
    """Limpia el texto para renderizado Markdown/LaTeX en Streamlit."""
    if not text: return ""
    # Evita conflictos con el símbolo '#' que Mistral a veces usa mal
    text = text.replace("#", " num. ")
    return text

async def call_tool_mcp(tool_name: str, arguments: dict):
    """Llama a la tool vía SSE (Requisito 4.3)."""
    try:
        async with sse_client(MCP_URL) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                # Timeout para robustez (Punto 5)
                async with asyncio.timeout(25.0):
                    result = await session.call_tool(tool_name, arguments=arguments)
                    return result.content
    except Exception as e:
        return f"Error en la llamada a la tool: {str(e)}"

def run_logic(prompt):
    """Puente entre el loop de Streamlit y la lógica async."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    return loop.run_until_complete(handle_query(prompt, call_tool_mcp))

# --- 3. INTERFAZ DE CHAT ---
st.title("🛡️ Asistente Técnico Híbrido")
st.caption("RAG Jerárquico (INCIBE) + Herramientas MCP Financieras")

if "messages" not in st.session_state:
    st.session_state.messages = []

# Mostrar historial
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])
        if "debug" in m and debug_mode:
            st.info(m["debug"])

# Input del usuario
if prompt := st.chat_input("Escribe tu consulta (Ej: ¿Está abierto Nasdaq? o resume la pág 4)"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Pensando y consultando fuentes..."):
            try:
                # Ejecutar Orquestador
                res_data = run_logic(prompt)
                
                # 1. Procesar respuesta principal
                answer = clean_llm_latex(res_data.get("answer", "No se obtuvo respuesta."))
                
                # 2. Construir visualización de Citaciones (Punto 4.2)
                citations_html = ""
                if res_data.get("citations"):
                    citations_html = f"\n\n---\n**📖 Fuentes:** {', '.join(set(res_data['citations']))}"
                
                full_response = answer + citations_html
                st.markdown(full_response)

                # 3. MODO DEPURACIÓN (Punto 4.1 y 13)
                debug_info = ""
                if debug_mode:
                    with st.expander("🔍 Trazabilidad (Debug)"):
                        st.write(f"**Ruta elegida:** `{res_data.get('route')}`")
                        
                        if res_data.get("tool_calls"):
                            st.write("**🛠️ MCP Tool Call:**")
                            st.json(res_data["tool_calls"])
                            
                        if res_data.get("citations"):
                            st.write("**📄 Chunks recuperados (Nivel 1):**")
                            # Aquí podrías mostrar fragmentos de texto si los pasas en res_data
                            st.write("Citas vinculadas a páginas: " + str(res_data["citations"]))

                # Guardar en historial
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": full_response,
                    "debug": debug_info if debug_mode else None
                })

            except Exception as e:
                st.error(f"Error crítico en el orquestador: {e}")
                st.exception(e)