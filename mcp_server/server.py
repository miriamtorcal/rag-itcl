import json
import time

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from mcp_server.utils import list_tools, call_tool

app = FastAPI()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/tools")
def tools():
    try:
        return {"tools": list_tools()}
    except Exception as e:
        return {"msg": "Error al cargar las tools", "ok": False, "error": str(e)}


@app.post("/call/{tool_name}")
def call(tool_name: str, payload: dict):
    start = time.time()
    try:
        result = call_tool(tool_name, payload)
        return {
            "tool_name": {tool_name},
            "ok": True,
            "result": result,
            "duration_ms": int((time.time() - start) * 1000),
        }
    except Exception as e:
        return {"tool_name": {tool_name}, "ok": False, "error": str(e)}

@app.get("/events")
def events(request: Request):
    def event_stream():
        yield f"event: tools\ndata: {json.dumps({'tools': list_tools()})}\n\n"
        while True:
            time.sleep(10)
    return StreamingResponse(event_stream(), media_type="text/event-stream")