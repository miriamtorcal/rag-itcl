from pathlib import Path
from dotenv import dotenv_values
import os

PROJECT_ROOT = Path(__file__).resolve().parents[2]

env_settings = dotenv_values(".env")

DATA_DIR = PROJECT_ROOT / "data"

FILE_PATH = os.getenv("FILE_PATH")
VECTORSTORE_PATH = os.getenv("VECTORSTORE_PATH")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL")
MAX_PAGES = int(os.getenv("MAX_PAGES"))
SCORE_THRESHOLD = float(os.getenv("SCORE_THRESHOLD"))
LOG_DIR = os.getenv("LOG_DIR")
LOG_FILE = os.getenv("LOG_FILE")
MCP_URL = os.getenv("MCP_URL")
OLLAMA_URL = os.getenv("OLLAMA_URL")


if FILE_PATH:
    FILE_PATH = Path(FILE_PATH)
    if not FILE_PATH.is_absolute():
        FILE_PATH = PROJECT_ROOT / DATA_DIR / FILE_PATH
else:
    FILE_PATH = PROJECT_ROOT / DATA_DIR / "pdf_example.pdf"
VECTORSTORE_PATH = PROJECT_ROOT / DATA_DIR / VECTORSTORE_PATH
