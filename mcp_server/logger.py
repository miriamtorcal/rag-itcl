import json
import logging
from pathlib import Path

log_file = Path("logs/app.log")
log_file.parent.mkdir(exist_ok=True)

logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format="%(message)s"
)

def log_event(event: dict):
    logging.info(json.dumps(event))