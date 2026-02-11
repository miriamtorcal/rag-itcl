from datetime import datetime, timezone
from mcp_server.utils import stable_int

def fx_rate_handler(base, quote):
    # valor mock realista: 0.5 – 1.5
    rate = 0.5 + stable_int(f"{base}:{quote}", 100) / 100
    return {
        "base": base,
        "quote": quote,
        "rate": round(rate, 2),
        "as_of": datetime.now(timezone.utc).isoformat()
    }


TOOL = {
    "name": "fx_rate",
    "description": "Obtiene tipo de cambio para un par base/quote",
    "input_schema": {
        "type": "object",
        "properties": {
            "base": {"type": "string"},
            "quote": {"type": "string"},
        },
    },
    "required": ["base", "quote"],
    "handler": lambda base, quote: fx_rate_handler(base, quote),
}
