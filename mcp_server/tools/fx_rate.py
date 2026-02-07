from datetime import datetime, timezone
from mcp_server.utils import stable_int

TOOL = {
    "name": "fx_rate",
    "description": "Obtiene tipo de cambio para un par base/quote",
    "input_schema": {
        "type": "object",
        "properties": {
            "base": {"type": "string"},
            "quote": {"type": "string"}
        }
    },
    "required": ["base", "quote"],
    "handler": lambda base, quote: {
        "base": base,
        "quote": quote,
        "rate": round(stable_int(f"{base}:{quote}", 200) / 100, 2), # Maximo 2 decimales y nunca llega a 2.00
        "as_of": datetime.now(timezone.utc).isoformat()
    }
}
