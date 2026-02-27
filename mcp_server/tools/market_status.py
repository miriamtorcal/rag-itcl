# rag-itcl/mcp_server/tools/market_status.py
import time
from pydantic import BaseModel
from mcp_server.logger import log_event

# -----------------------------
# Input Model profesional
# -----------------------------
class MarketStatusInput(BaseModel):
    market: str  # Identificador del mercado, ejemplo: "NASDAQ"

# -----------------------------
# Tool
# -----------------------------
def market_status(input: MarketStatusInput) -> dict:
    start = time.time()
    result = {
        "market": input.market,
        "is_open": True,  # mock de estado
        "as_of": "2026-01-01T10:00:00Z"
    }
    duration = time.time() - start

    # logging profesional
    log_event({
        "tool": "market_status",
        "args": {"market": input.market},
        "duration": duration,
        "status": "ok"
    })
    return result

# Flag para habilitar/deshabilitar dinámicamente
market_status.enabled = True

# Para registro dinámico en server.py
__all__ = ["market_status"]