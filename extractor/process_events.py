"""
Fetch traffic events (أحداث مرورية) from the events API, classify each one into a
sub-category (subcategory.txt) then extract structured fields (schemaextractevent.txt)
from event_summary using Ollama. event_place and subject are copied verbatim from the
source event, never re-derived by the model.

Configuration lives in .env (see .env.example): API_BASE_URL, START_DATE, CATEGORY,
CLASSIFICATION_MODEL, EXTRACTION_MODEL, USE_SAMPLE_DATA, ...
"""

import argparse
import json
import os
import re
import sys
import uuid
from pathlib import Path

import requests
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

API_BASE_URL = os.getenv("API_BASE_URL", "http://172.19.0.37:8003").rstrip("/")
EVENTS_PATH = os.getenv("EVENTS_PATH", "/events")
START_PARAM = os.getenv("START_PARAM", "start")
CATEGORY_PARAM = os.getenv("CATEGORY_PARAM", "category")
START_DATE = os.getenv("START_DATE", "2026-08-18T00:00:00")
CATEGORY = os.getenv("CATEGORY", "أحداث مرورية")
REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "30"))

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
OLLAMA_TIMEOUT = float(os.getenv("OLLAMA_TIMEOUT", "120"))
CLASSIFICATION_MODEL = os.getenv("CLASSIFICATION_MODEL", "llama3.2:1b")
EXTRACTION_MODEL = os.getenv("EXTRACTION_MODEL", "llama3.2:1b")

USE_SAMPLE_DATA = os.getenv("USE_SAMPLE_DATA", "false").strip().lower() in ("1", "true", "yes")
SAMPLE_DATA_FILE = BASE_DIR / os.getenv("SAMPLE_DATA_FILE", "data.json.txt")
SUBCATEGORY_FILE = BASE_DIR / os.getenv("SUBCATEGORY_FILE", "subcategory.txt")


def log(*args):
    print(*args, file=sys.stderr)


# ---------------------------------------------------------------------------
# Reference data
# ---------------------------------------------------------------------------
_CATEGORY_BLOCK_RE = re.compile(r'"([^"]+)"\s*:\s*\[(.*?)\]', re.DOTALL)
_STRING_RE = re.compile(r'"([^"]+)"')


def load_subcategories(path: Path, category: str) -> list:
    """subcategory.txt is a loose (trailing-comma) JSON fragment, so it is parsed
    with regex instead of json.loads."""
    text = path.read_text(encoding="utf-8")
    for match in _CATEGORY_BLOCK_RE.finditer(text):
        if match.group(1) == category:
            return _STRING_RE.findall(match.group(2))
    raise ValueError(f"category {category!r} not found in {path}")


# ---------------------------------------------------------------------------
# Fetching events
# ---------------------------------------------------------------------------
def fetch_events() -> list:
    if USE_SAMPLE_DATA:
        log(f"[data] USE_SAMPLE_DATA=true -> reading {SAMPLE_DATA_FILE}")
        return json.loads(SAMPLE_DATA_FILE.read_text(encoding="utf-8"))

    url = f"{API_BASE_URL}{EVENTS_PATH}"
    params = {START_PARAM: START_DATE, CATEGORY_PARAM: CATEGORY}
    log(f"[api] GET {url} params={params}")
    try:
        resp = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as exc:
        log(f"[api] request failed ({exc}); falling back to sample data at {SAMPLE_DATA_FILE}")
        return json.loads(SAMPLE_DATA_FILE.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Ollama calls (raw REST API, so this works regardless of the ollama pip client version)
# ---------------------------------------------------------------------------
def ollama_chat_json(model: str, prompt: str, schema: dict) -> dict:
    url = f"{OLLAMA_HOST}/api/chat"
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "format": schema,
        "stream": False,
        "options": {"temperature": 0},
    }
    resp = requests.post(url, json=payload, timeout=OLLAMA_TIMEOUT)
    resp.raise_for_status()
    content = resp.json()["message"]["content"]
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def classify_subcategory(event_summary: str, subcategories: list) -> dict:
    schema = {
        "type": "object",
        "properties": {
            "الصنف_الفرعي": {"type": "string", "enum": subcategories},
            "نسبة_الثقة": {"type": "number", "minimum": 0, "maximum": 1},
        },
        "required": ["الصنف_الفرعي", "نسبة_الثقة"],
    }
    prompt = (
        "أنت محلل مختص في تصنيف بلاغات حوادث المرور.\n"
        "صنّف نص الحدث التالي ضمن إحدى الفئات الفرعية المتاحة فقط، واختر الأقرب دلاليًا لمضمون النص.\n\n"
        "الفئات الفرعية المتاحة:\n" + "\n".join(f"- {c}" for c in subcategories) + "\n\n"
        f"نص الحدث:\n{event_summary}\n\n"
        "أعد فقط كائن JSON بالصنف الفرعي المختار (بنفس الصياغة الحرفية من القائمة أعلاه) ونسبة ثقة بين 0 و1."
    )
    return ollama_chat_json(CLASSIFICATION_MODEL, prompt, schema)


def build_extraction_schema() -> dict:
    return {
        "type": "object",
        "properties": {
            "الحالة": {
                "type": "object",
                "properties": {
                    "وضعية_الحدث": {"type": "string", "enum": ["مفتوح", "مغلق", "قيد_المعالجة"]},
                    "الخطورة": {"type": "string", "enum": ["منخفض", "متوسط", "مرتفع", "حرج"]},
                    "الأولوية": {"type": "integer", "minimum": 1, "maximum": 5},
                },
                "required": ["وضعية_الحدث", "الخطورة", "الأولوية"],
            },
            "الوصف": {
                "type": "object",
                "properties": {
                    "تفاصيل": {"type": "string"},
                    "كلمات_مفتاحية": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["تفاصيل", "كلمات_مفتاحية"],
            },
            "الموقع": {
                "type": "object",
                "properties": {"المنطقة": {"type": "string"}},
                "required": ["المنطقة"],
            },
            "الأطراف": {
                "type": "object",
                "properties": {
                    "السائقون": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "الاسم": {"type": "string"},
                                "الرخصة": {"type": "string"},
                            },
                        },
                    },
                    "الضحايا": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {"العدد": {"type": "integer"}},
                        },
                    },
                },
                "required": ["السائقون", "الضحايا"],
            },
            "تفاصيل_الحادث": {
                "type": "object",
                "properties": {
                    "نوع_الحادث": {"type": "string"},
                    "عدد_المركبات": {"type": "integer"},
                    "عدد_الإصابات": {"type": "integer"},
                    "عدد_الوفيات": {"type": "integer"},
                    "حالة_الطريق": {"type": "string"},
                    "مواد_خطرة_متسربة": {"type": "boolean"},
                },
                "required": [
                    "نوع_الحادث",
                    "عدد_المركبات",
                    "عدد_الإصابات",
                    "عدد_الوفيات",
                    "حالة_الطريق",
                    "مواد_خطرة_متسربة",
                ],
            },
            "التدقيق": {
                "type": "object",
                "properties": {
                    "تم_الإبلاغ_من": {"type": "string"},
                    "حالة_التحقق": {"type": "string", "enum": ["قيد_الانتظار", "مؤكد", "مرفوض"]},
                },
                "required": ["تم_الإبلاغ_من", "حالة_التحقق"],
            },
        },
        "required": ["الحالة", "الوصف", "الموقع", "الأطراف", "تفاصيل_الحادث", "التدقيق"],
    }


def extract_details(event_summary: str, subject: str) -> dict:
    prompt = (
        "أنت محلل بيانات لأحداث المرور. استخرج المعلومات المطلوبة حصرًا من النص التالي بدقة، "
        "دون اختلاق معلومات غير موجودة فيه.\n\n"
        f"عنوان الحدث: {subject}\n\n"
        f"نص الحدث:\n{event_summary}\n\n"
        "أعد النتيجة ككائن JSON مطابق للمخطط المطلوب فقط."
    )
    return ollama_chat_json(EXTRACTION_MODEL, prompt, build_extraction_schema())


# ---------------------------------------------------------------------------
# Assembling the final record (schemaextractevent.txt)
# ---------------------------------------------------------------------------
def build_event_record(event: dict, subcategory: dict, extraction: dict) -> dict:
    return {
        "معرف_الحدث": event.get("reference") or str(uuid.uuid4()),
        "المصدر": event.get("source"),
        "الطوابع_الزمنية": {
            "وقت_الإنشاء": None,
            "وقت_التحديث": None,
            "وقت_الحدث": event.get("time"),
        },
        "التصنيف": {
            "الصنف_الرئيسي": CATEGORY,
            "الصنف_الفرعي": subcategory.get("الصنف_الفرعي"),
            "نسبة_الثقة": subcategory.get("نسبة_الثقة"),
        },
        "الحالة": extraction.get("الحالة", {}),
        "الوصف": {
            "عنوان": event.get("subject"),  # kept as-is, not LLM-derived
            "تفاصيل": extraction.get("الوصف", {}).get("تفاصيل"),
            "كلمات_مفتاحية": extraction.get("الوصف", {}).get("كلمات_مفتاحية", []),
        },
        "الموقع": {
            "العنوان": event.get("event_place"),  # kept as-is, not LLM-derived
            "المنطقة": extraction.get("الموقع", {}).get("المنطقة"),
        },
        "الأطراف": extraction.get("الأطراف", {}),
        "تفاصيل_الحادث": extraction.get("تفاصيل_الحادث", {}),
        "التدقيق": extraction.get("التدقيق", {}),
        "النص_الأصلي": event.get("event_summary"),
    }


def process_event(event: dict, subcategories: list):
    summary = (event.get("event_summary") or "").strip()
    if not summary:
        log(f"[skip] reference={event.get('reference')} has empty event_summary")
        return None

    log(f"[classify] reference={event.get('reference')} model={CLASSIFICATION_MODEL}")
    subcategory = classify_subcategory(summary, subcategories)

    log(f"[extract] reference={event.get('reference')} model={EXTRACTION_MODEL}")
    extraction = extract_details(summary, event.get("subject") or "")

    return build_event_record(event, subcategory, extraction)


def main():
    parser = argparse.ArgumentParser(description="Classify & extract traffic events via Ollama")
    parser.add_argument("--limit", type=int, default=None, help="process only the first N events")
    args = parser.parse_args()

    subcategories = load_subcategories(SUBCATEGORY_FILE, CATEGORY)
    events = fetch_events()
    log(f"[data] fetched {len(events)} event(s), start={START_DATE} category={CATEGORY}")

    if args.limit:
        events = events[: args.limit]

    for event in events:
        try:
            record = process_event(event, subcategories)
        except Exception as exc:
            log(f"[error] reference={event.get('reference')}: {exc}")
            continue
        if record is None:
            continue
        print(json.dumps(record, ensure_ascii=False, indent=2))
        print()


if __name__ == "__main__":
    main()
