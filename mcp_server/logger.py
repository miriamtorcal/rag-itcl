import json
import logging
import os
from datetime import datetime, timezone

LOG_DIR = "logs"
LOG_FILE = "logs/app.log"
os.makedirs(LOG_DIR, exist_ok=True)

logger = logging.getLogger("mcp_itcl")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    file_handler = logging.FileHandler(LOG_FILE)
    file_handler.setFormatter(formatter)

    logger.addHandler(file_handler)

def log_event(event: dict, event_type: str = "mcp"):
    event["event_type"] = event_type
    event["component"] = "MCP_SERVER"
    event["timestamp"] = datetime.now(timezone.utc).isoformat()
    logger.info(json.dumps(event))
