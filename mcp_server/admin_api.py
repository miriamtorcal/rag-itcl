import asyncio
import json
from typing import Any, Dict

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from mcp_server.server import mcp
from mcp_server.logger import log_event

app = FastAPI(title="ITCL MCP Admin API")


class ToolCallResult(BaseModel):
    ok: bool
    result: Dict[str, Any] = None
    error: str = None
    duration: float = None


@app.get("/tools")
async def tools():
    tools_list = []
    registered_tools = await mcp.list_tools()
    for tool in registered_tools:
        tools_list.append(
            {
                "name": tool.name,
                "input_schema": getattr(tool, "inputSchema", {}),
            }
        )
    return {"tools": tools_list}


@app.post("/call/{tool_name}", response_model=ToolCallResult)
async def call_tool(tool_name: str, payload: Dict[str, Any]):
    tool = next((t for t in await mcp.list_tools() if t.name == tool_name), None)
    if not tool:
        raise HTTPException(status_code=404, detail="Tool no encontrada")

    start = asyncio.get_event_loop().time()

    try:
        raw_result = await mcp.call_tool(tool_name, {"input": payload})

        parsed_result = {}

        if isinstance(raw_result, list) and raw_result:
            content = raw_result[0]
            if hasattr(content, "text"):
                try:
                    parsed_result = json.loads(content.text)
                except:
                    parsed_result = {"text": content.text}

        duration = asyncio.get_event_loop().time() - start

        log_event({
            "tool": tool_name,
            "args": payload,
            "duration": duration,
            "status": "ok"
        })

        return ToolCallResult(ok=True, result=parsed_result, duration=duration)

    except Exception as e:
        duration = asyncio.get_event_loop().time() - start
        log_event({
            "tool": tool_name,
            "args": payload,
            "duration": duration,
            "status": "error",
            "error": str(e)
        })
        raise HTTPException(status_code=500, detail=str(e))