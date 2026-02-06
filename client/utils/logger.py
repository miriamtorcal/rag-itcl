import json
import logging
import os
from datetime import datetime

from client.utils.settings import LOG_DIR, LOG_FILE

LOG_FILE = os.path.join(LOG_DIR, LOG_FILE)
os.makedirs(LOG_DIR, exist_ok=True)

logger = logging.getLogger("rag_itcl")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    file_handler = logging.FileHandler(LOG_FILE)
    file_handler.setFormatter(formatter)

    logger.addHandler(file_handler)

def log_event(event: dict, event_type: str = "rag"):
    event["event_type"] = event_type
    event["timestamp"] = datetime.now(datetime.timezone.utc).isoformat()
    logger.info(json.dumps(event))
