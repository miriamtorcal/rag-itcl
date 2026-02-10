from pathlib import Path
from dotenv import dotenv_values

PROJECT_ROOT = Path(__file__).resolve().parents[2]

env_settings = dotenv_values(PROJECT_ROOT / ".env")

DATA_DIR = PROJECT_ROOT / "data"

FILE_PATH = env_settings.get("FILE_PATH")
VECTORSTORE_PATH = env_settings.get("VECTORSTORE_PATH")
EMBEDDING_MODEL = env_settings.get("EMBEDDING_MODEL")
MAX_PAGES = int(env_settings.get("MAX_PAGES"))
SCORE_THRESHOLD = float(env_settings.get("SCORE_THRESHOLD"))
LOG_DIR = env_settings.get("LOG_DIR")
LOG_FILE = env_settings.get("LOG_FILE")
ROUTER_LLM_MODEL = env_settings.get("ROUTER_LLM_MODEL")
MCP_URL = env_settings.get("MCP_URL")


if FILE_PATH:
    FILE_PATH = Path(FILE_PATH)
    if not FILE_PATH.is_absolute():
        FILE_PATH = PROJECT_ROOT / DATA_DIR / FILE_PATH
else:
    FILE_PATH = PROJECT_ROOT / DATA_DIR / "pdf_example.pdf"
VECTORSTORE_PATH = PROJECT_ROOT / DATA_DIR / VECTORSTORE_PATH
