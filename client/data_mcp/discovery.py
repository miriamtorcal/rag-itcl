import asyncio
import json
from mcp import ClientSession
from mcp.client.sse import sse_client
from client.utils.settings import MCP_URL

async def discover_tools():
    try:
        async with sse_client(MCP_URL) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                
                # 💡 PAUSA DE SEGURIDAD AUMENTADA
                print("DEBUG: ⏳ Esperando a que el servidor asiente la sesión...", flush=True)
                await asyncio.sleep(2.0) 
                
                response = await session.list_tools()
                return [{"name": t.name, "description": t.description} for t in response.tools]
    except Exception as e:
        print(f"DEBUG: ❌ Error en Discovery: {e}", flush=True)
        return []