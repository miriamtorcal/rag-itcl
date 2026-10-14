import asyncio
import logging
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.responses import Response
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import Tool, TextContent

# Configuración de Logs para ver qué pasa en tiempo real
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp_server")

# 1. Inicialización ÚNICA del Servidor
server = Server("financial-logic-server")

@server.list_tools()
async def handle_list_tools():
    return [
        Tool(
            name="fx_rate",
            description="Convierte divisas. Requiere 'to_currency'.",
            inputSchema={
                "type": "object",
                "properties": {
                    "amount": {"type": "number"},
                    "to_currency": {"type": "string"},
                },
                "required": ["to_currency"],
            },
        ),
        Tool(
            name="market_status",
            description="Estado del mercado basado en la longitud de su nombre.",
            inputSchema={
                "type": "object",
                "properties": {"market": {"type": "string"}},
                "required": ["market"], # Obligatorio, sin valores por defecto
            },
        ),
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict):
    try:
        if name == "market_status":
            market = arguments.get("market")
            if not market:
                raise ValueError("El parámetro 'market' es obligatorio.")
            
            # --- NUEVA LÓGICA DE LONGITUD ---
            m_name = str(market).strip()
            longitud = len(m_name)
            # Par = ABIERTO, Impar = CERRADO
            status = "ABIERTO" if longitud % 2 == 0 else "CERRADO"
            
            return [TextContent(type="text", text=f"🔧 Mercado: {m_name} (Longitud: {longitud}) -> Estado: {status}")]

        if name == "fx_rate":
            # Lógica simple para fx_rate
            to_curr = arguments.get("to_currency", "USD")
            return [TextContent(type="text", text=f"🔧 Tasa para {to_curr}: 1.25 (Simulado)")]

        raise ValueError(f"Herramienta {name} no encontrada")
    except Exception as e:
        logger.error(f"Error en tool: {e}")
        return [TextContent(type="text", text=f"⚠️ Error: {str(e)}")]

# 2. Infraestructura SSE (UNA SOLA INSTANCIA)
sse = SseServerTransport("/messages")

async def handle_sse(request):
    """Maneja el GET /sse"""
    async with sse.connect_sse(request.scope, request.receive, request._send) as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())

async def handle_messages(request):
    """
    Maneja el POST /messages.
    CORRECCIÓN: Pasamos scope, receive y send directamente como pide tu versión.
    """
    try:
        # El log indicó que faltaban receive y send. Se los pasamos así:
        await sse.handle_post_message(request.scope, request.receive, request._send)
        
        # IMPORTANTE: Retornar Response para evitar el error 'NoneType' object is not callable
        return Response(status_code=202)
    except Exception as e:
        logger.error(f"💥 Error en POST: {e}")
        return Response(content=str(e), status_code=500)

# 3. App Starlette
app = Starlette(
    routes=[
        Route("/sse", endpoint=handle_sse),
        Route("/messages", endpoint=handle_messages, methods=["POST"]),
    ]
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)