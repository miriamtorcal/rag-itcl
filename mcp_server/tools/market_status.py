import random
from datetime import datetime,timezone

from mcp_server.utils import stable_int

TOOL = {
    "name": "market_status",
    "description": "Consulta si un mercado está abierto",
    "input_schema": {
        "type": "object",
        "properties": {
            "market": {"type":"string"}
        }
    },
    "required": ["market"],
    "handler": lambda market: {
        "market": market,
        "is_open": stable_int(market, 2) == 1,
        "as_of": datetime.now(timezone.utc).isoformat()
    }
}
