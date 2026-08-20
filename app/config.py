import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://morour:morour@db:5432/morour")

API_BASE_URL = os.getenv("API_BASE_URL", "http://172.19.0.37:8003").rstrip("/")
EVENTS_PATH = os.getenv("EVENTS_PATH", "/events")
START_PARAM = os.getenv("START_PARAM", "start")
CATEGORY_PARAM = os.getenv("CATEGORY_PARAM", "category")
DEFAULT_START_DATE = os.getenv("START_DATE", "2026-08-18T00:00:00")
CATEGORY = os.getenv("CATEGORY", "أحداث مرورية")
REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "30"))

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://host.docker.internal:11434").rstrip("/")
OLLAMA_TIMEOUT = float(os.getenv("OLLAMA_TIMEOUT", "120"))
CLASSIFICATION_MODEL = os.getenv("CLASSIFICATION_MODEL", "llama3.2:1b")
EXTRACTION_MODEL = os.getenv("EXTRACTION_MODEL", "llama3.2:1b")

USE_SAMPLE_DATA = os.getenv("USE_SAMPLE_DATA", "false").strip().lower() in ("1", "true", "yes")
SAMPLE_DATA_FILE = BASE_DIR / os.getenv("SAMPLE_DATA_FILE", "data.json.txt")
SUBCATEGORY_FILE = BASE_DIR / os.getenv("SUBCATEGORY_FILE", "subcategory.txt")

# How often the worker polls the source API for new events, and how far back
# (in minutes) it re-queries past the latest event time it already saw, as a
# safety margin against events landing slightly out of order.
POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", "60"))
POLL_OVERLAP_MINUTES = int(os.getenv("POLL_OVERLAP_MINUTES", "5"))
