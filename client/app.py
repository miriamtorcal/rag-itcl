import sys
from pathlib import Path
import streamlit as st

# --- Fix imports ---
ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from client.router import handle_query
from client.utils.logger import log_event

# --- Config ---
st.set_page_config(page_title="RAG + Tools Chat", layout="wide")
st.title("Asistente RAG + MCP Tools")

# --- Estado ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "show_debug" not in st.session_state:
    st.session_state.show_debug = False

# --- Header con botón Debug ---
col1, col2 = st.columns([8, 1])

with col2:
    if st.button("🐛 Debug", key="debug_toggle"):
        st.session_state.show_debug = not st.session_state.show_debug

# --- Input tipo chat ---
query = st.chat_input("Escribe tu pregunta")

if query:
    response = handle_query(query)
    st.session_state.chat_history.append(
        {"query": query, "response": response}
    )
        # Guardar en log
    log_event({
        "query": query,
        "response": response
    })

# --- Render chat ---
for chat in st.session_state.chat_history:
    with st.chat_message("user"):
        st.markdown(chat["query"])

    with st.chat_message("assistant"):
        st.markdown(chat["response"]["answer"])
        st.caption(f"Ruta: {chat['response']['route']}")

        if chat["response"]["citations"]:
            with st.expander("📄 Citas"):
                for c in chat["response"]["citations"]:
                    st.markdown(f"- p.{c['page']} — {c['chunk_id']}")

# --- Debug global ---
if st.session_state.show_debug:
    st.subheader("🧾 Debug")
    for chat in st.session_state.chat_history[::-1]:
        st.json(chat["response"]["debug"])
