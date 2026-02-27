import time
from pydantic import BaseModel
from mcp_server.logger import log_event

# Input Model ordenado y profesional
class FxRateInput(BaseModel):
    base: str  # moneda base, ejemplo: "EUR"
    quote: str  # moneda destino, ejemplo: "USD"

# Tool
def fx_rate(input: FxRateInput) -> dict:
    start = time.time()
    # lógica de ejemplo
    result = {
        "base": input.base,
        "quote": input.quote,
        "rate": 1.08,  # valor de ejemplo
        "as_of": "2026-01-01T00:00:00Z",
    }
    duration = time.time() - start

    # logging profesional
    log_event({
        "tool": "fx_rate",
        "args": {"base": input.base, "quote": input.quote},
        "duration": duration,
        "status": "ok"
    })
    return result

# Flag para habilitar/deshabilitar dinámicamente
fx_rate.enabled = True

# Para registro dinámico en server.py
__all__ = ["fx_rate"]