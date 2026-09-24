import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://morour:morour@db:5432/morour")

API_BASE_URL = os.getenv("API_BASE_URL", "http://172.19.0.37:8003").rstrip("/")
EVENTS_PATH = os.getenv("EVENTS_PATH", "/events")
START_PARAM = os.getenv("START_PARAM", "start")
DEFAULT_START_DATE = os.getenv("START_DATE", "2026-08-18T00:00:00")
CATEGORY = os.getenv("CATEGORY", "أحداث مرورية")
REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "30"))
# Confirmed from the source API's own openapi.json: /events paginates via
# page (1-indexed) + page_size (default 50) — not offset/skip.
EVENTS_PAGE_SIZE = int(os.getenv("EVENTS_PAGE_SIZE", "50"))

VLLM_HOST = os.getenv("VLLM_HOST", "http://vllm:8000").rstrip("/")
# An 8B is an order of magnitude slower per call than the 1B this replaced, and a
# cold grammar compile on the first guided request adds to it — hence minutes,
# not the 120s Ollama needed.
VLLM_TIMEOUT = float(os.getenv("VLLM_TIMEOUT", "300"))
# Hard cap on generated tokens per call. A normal extraction is ~250-500 tokens;
# without a cap a model stuck repeating itself runs until VLLM_TIMEOUT and
# returns nothing. With it, the call ends early with finish_reason=length.
VLLM_MAX_TOKENS = int(os.getenv("VLLM_MAX_TOKENS", "1536"))
# Qwen3 is a hybrid reasoning model: left on, it emits <think> blocks that
# collide with schema-guided decoding and corrupt the JSON. Every call below
# forces it off; this exists only so it can be turned back on for debugging.
VLLM_ENABLE_THINKING = os.getenv("VLLM_ENABLE_THINKING", "false").strip().lower() in ("1", "true", "yes")
# A failed row is retried on later cycles until it has failed this many times.
MAX_CLASSIFY_ATTEMPTS = int(os.getenv("MAX_CLASSIFY_ATTEMPTS", "3"))
# vLLM serves one model per process, so both of these must name the same model
# unless you also run a second vLLM container for the other one.
CLASSIFICATION_MODEL = os.getenv("CLASSIFICATION_MODEL", "Qwen/Qwen3-8B-AWQ")
EXTRACTION_MODEL = os.getenv("EXTRACTION_MODEL", "Qwen/Qwen3-8B-AWQ")

USE_SAMPLE_DATA = os.getenv("USE_SAMPLE_DATA", "false").strip().lower() in ("1", "true", "yes")
SAMPLE_DATA_FILE = BASE_DIR / os.getenv("SAMPLE_DATA_FILE", "data.json.txt")
SUBCATEGORY_FILE = BASE_DIR / os.getenv("SUBCATEGORY_FILE", "subcategory.txt")

# How often the worker polls the source API for new events, and how far back
# (in minutes) it re-queries past the latest event time it already saw, as a
# safety margin against events landing slightly out of order.
POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", "60"))
POLL_OVERLAP_MINUTES = int(os.getenv("POLL_OVERLAP_MINUTES", "5"))
