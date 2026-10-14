# rag-itcl/mcp_server/server.py
import asyncio
import importlib
import json
import pkgutil
from typing import Any, Dict

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

from mcp_server.logger import log_event  # logging centralizado

# -----------------------------
# Inicializar FastMCP
# -----------------------------
mcp = FastMCP("ITCL MCP Server")

# -----------------------------
# Cargar dinámicamente todas las tools desde mcp_server/tools/
# -----------------------------
tools_package = "mcp_server.tools"
for _, modname, ispkg in pkgutil.iter_modules([tools_package.replace(".", "/")]):
    module = importlib.import_module(f"{tools_package}.{modname}")
    for tool_name in getattr(module, "__all__", []):
        tool_func = getattr(module, tool_name)
        mcp.tool()(tool_func)  # registramos la tool en FastMCP


# -----------------------------
# Pydantic model para llamadas de tools
# -----------------------------
class ToolCallResult(BaseModel):
    ok: bool
    result: Dict[str, Any] = None
    error: str = None
    duration: float = None


# -----------------------------
# FastAPI app
# -----------------------------
app = FastAPI(title="ITCL MCP Server")


# -----------------------------
# Listar tools
# -----------------------------
@app.get("/tools")
async def tools():
    tools_list = []
    registered_tools = await mcp.list_tools()
    for tool in registered_tools:
        tools_list.append(
            {
                "name": tool.name,
                "enabled": getattr(tool, "enabled", True),
                "input_schema": getattr(tool, "inputSchema", {}),
            }
        )
    return {"tools": tools_list}


# -----------------------------
# Llamar tool por nombre
# -----------------------------
@app.post("/call/{tool_name}", response_model=ToolCallResult)
async def call_tool_endpoint(tool_name: str, payload: Dict[str, Any]):
    # buscamos la tool
    tool = next((t for t in await mcp.list_tools() if t.name == tool_name), None)
    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' no encontrada")
    if not getattr(tool, "enabled", True):
        raise HTTPException(status_code=400, detail=f"Tool '{tool_name}' deshabilitada")

    start = asyncio.get_event_loop().time()
    payload_complete = {"input": payload}

    try:
        raw_result = await mcp.call_tool(tool_name, payload_complete)

        parsed_result: Dict[str, Any] = {}

        if isinstance(raw_result, list) and raw_result:
            content = raw_result[0]

            if hasattr(content, "text") and content.text:
                text = content.text.strip()

                # Si es JSON → convertir a dict
                try:
                    parsed_result = json.loads(text)
                except json.JSONDecodeError:
                    parsed_result = {"text": text}
            else:
                parsed_result = {"raw": str(content)}
        else:
            parsed_result = {"raw": str(raw_result)}

        duration = asyncio.get_event_loop().time() - start

        log_event(
            {"tool": tool_name, "args": payload, "duration": duration, "status": "ok"}
        )

        return ToolCallResult(ok=True, result=parsed_result, duration=duration)

    except Exception as e:
        duration = asyncio.get_event_loop().time() - start
        log_event(
            {
                "tool": tool_name,
                "args": payload,
                "duration": duration,
                "status": "error",
                "error": str(e),
            }
        )
        raise HTTPException(status_code=500, detail=str(e))


# -----------------------------
# Toggle tool dinámicamente
# -----------------------------
@app.post("/toggle_tool/{tool_name}")
async def toggle_tool(tool_name: str, enabled: bool):
    tool = next((t for t in await mcp.list_tools() if t.name == tool_name), None)
    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' no encontrada")
    print(f"Tool -> {tool}")
    tool.enabled = enabled
    log_event({"tool": tool_name, "enabled": enabled, "action": "toggle"})
    return {"tool": tool_name, "enabled": enabled}


# -----------------------------
# SSE para tools
# -----------------------------
@app.get("/events")
async def events():
    async def event_stream():
        while True:
            registered_tools = await mcp.list_tools()
            tools_names = [t.name for t in registered_tools]
            yield f"event: tools\ndata: {tools_names}\n\n"
            await asyncio.sleep(10)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# -----------------------------
# Run server con FastMCP SSE
# -----------------------------
if __name__ == "__main__":
    mcp.run(transport="streamable-http")
