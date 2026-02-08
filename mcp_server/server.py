import json
import time

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse

from mcp_server.utils import call_tool, list_tools
from mcp_server.logger import log_event

app = FastAPI()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/tools")
def tools():
    try:
        result = {"tools": list_tools()}
        log_event(result)
        return result
    except Exception as e:
        err = {"msg": "Error al cargar las tools", "ok": False, "error": str(e)}
        log_event(err)
        return err


@app.post("/call/{tool_name}")
def call(tool_name: str, payload: dict):
    start = time.time()
    try:
        result = call_tool(tool_name, payload)
        result_info = {
            "tool_name": tool_name,
            "ok": True,
            "result": result,
            "duration_ms": int((time.time() - start) * 1000),
        }
        log_event(result_info)
        return result_info
    except Exception as e:
        err_info = {"tool_name": tool_name, "ok": False, "error": str(e)}
        log_event(err_info)
        return err_info


@app.get("/events")
def events(request: Request):
    def event_stream():
        yield f"event: tools\ndata: {json.dumps({'tools': list_tools()})}\n\n"
        while True:
            time.sleep(10)

    return StreamingResponse(event_stream(), media_type="text/event-stream")
