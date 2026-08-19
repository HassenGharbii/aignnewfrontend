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

# Windows consoles/pipes often default stdout/stderr to a non-UTF-8 codepage,
# which crashes on Arabic text. Force UTF-8 so output never depends on locale.
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

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


def dedupe_events(events: list) -> list:
    """The same case is often relayed multiple times under the same reference as it
    moves through the reporting chain (duty officer -> central room -> region, ...),
    with identical event_summary text each time. Classifying/extracting it repeatedly
    wastes LLM calls, so keep only the first occurrence per reference."""
    seen = set()
    deduped = []
    for event in events:
        reference = event.get("reference")
        if reference is not None and reference in seen:
            continue
        if reference is not None:
            seen.add(reference)
        deduped.append(event)
    dropped = len(events) - len(deduped)
    if dropped:
        log(f"[data] dropped {dropped} duplicate-reference event(s)")
    return deduped


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
        "think": False,
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


def classify_subcategory(event_summary: str, subject: str, subcategories: list) -> dict:
    schema = {
        "type": "object",
        "properties": {
            "الصنف_الفرعي": {"type": "string", "enum": subcategories},
            "نسبة_الثقة": {"type": "number", "minimum": 0, "maximum": 1},
        },
        "required": ["الصنف_الفرعي", "نسبة_الثقة"],
    }
    # نص الحدث/عنوان الحدث are placed first so this call shares an identical prompt
    # prefix with extract_details() for the same event, letting Ollama reuse the
    # KV-cache prefill across both calls instead of reprocessing the text twice.
    prompt = (
        f"نص الحدث:\n{event_summary}\n\n"
        f"عنوان الحدث: {subject}\n\n"
        "أنت محلل مختص في تصنيف بلاغات حوادث المرور.\n"
        "صنّف نص الحدث أعلاه ضمن إحدى الفئات الفرعية المتاحة فقط، واختر الأقرب دلاليًا لمضمون النص.\n"
        "اعتمد في اختيارك على \"نتيجة الحادث\" الفعلية (وجود إصابات بدنية، وفيات، حريق...) "
        "وليس على \"الأسباب المحتملة\" المذكورة عادة في نهاية النص (مثل وجود زيت أو مواد على "
        "الطريق) — هذه الأسباب لا تُصنَّف كحدث بيئي إلا إذا لم ينتج عنها حادث فعلي بمركبة.\n\n"
        "الفئات الفرعية المتاحة:\n" + "\n".join(f"- {c}" for c in subcategories) + "\n\n"
        "أعد فقط كائن JSON بالصنف الفرعي المختار (بنفس الصياغة الحرفية من القائمة أعلاه) ونسبة ثقة بين 0 و1."
    )
    return ollama_chat_json(CLASSIFICATION_MODEL, prompt, schema)


ROAD_TYPES = [
    "طرق وطنية",
    "طرق جهوية",
    "طرق محلية",
    "مسالك فلاحية",
    "طرق أخرى",
    "طرق صغرى غير مرقّمة",
]

# Everything below used to be split into one schema section per Ollama call, to
# avoid a large combined grammar timing out on a 1B model. Now that الحالة/التدقيق
# were dropped and الوصف collapsed to just كلمات_مفتاحية, the remaining schema is
# small enough to ask for in a single call — cutting 4 round-trips (each re-sending
# and re-processing the full event text) down to 1.
EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "كلمات_مفتاحية": {"type": "array", "items": {"type": "string"}},
        "الموقع": {
            "type": "object",
            "properties": {
                "المنطقة": {"type": "string"},
                "المعتمدية": {"type": "string"},
                "العمادة": {"type": "string"},
            },
            "required": ["المنطقة", "المعتمدية", "العمادة"],
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
                        "properties": {"العدد": {"type": "integer", "minimum": 0, "maximum": 200}},
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
                "نوع_الطريق": {"type": "string", "enum": ROAD_TYPES},
                "مواد_خطرة_متسربة": {"type": "boolean"},
            },
            "required": [
                "نوع_الحادث",
                "عدد_المركبات",
                "عدد_الإصابات",
                "عدد_الوفيات",
                "حالة_الطريق",
                "نوع_الطريق",
                "مواد_خطرة_متسربة",
            ],
        },
    },
    "required": ["كلمات_مفتاحية", "الموقع", "الأطراف", "تفاصيل_الحادث"],
}

EXTRACTION_INSTRUCTIONS = (
    "أنت محلل بيانات لأحداث المرور. استخرج الحقول التالية من النص أعلاه بدقة، دون اختلاق "
    "معلومات غير موجودة فيه:\n\n"
    "- كلمات_مفتاحية: 3 إلى 6 عبارات قصيرة (كلمة إلى 4 كلمات) تمثل كيانات أو مواضيع رئيسية "
    "في النص (مثال: نوع المركبة، سبب الحادث، الجهة المتدخلة)، وليست جملًا كاملة أو نسخًا من النص.\n\n"
    "- الموقع: استخرج ثلاثة مستويات منفصلة بالارتباط الحرفي بكلمتها الدالة في النص، ولا "
    "تخمّن قيمة لمستوى لم يُذكر صراحة:\n"
    "  - المنطقة: الاسم الوارد بعد كلمة \"حي\" أو \"منطقة\".\n"
    "  - المعتمدية: الاسم الوارد بعد كلمة \"معتمدية\" حرفيًا فقط.\n"
    "  - العمادة: الاسم الوارد بعد كلمة \"عمادة\" حرفيًا فقط — لا تضع فيها اسم الولاية أو "
    "المعتمدية أو المنطقة إن لم تَرِد كلمة \"عمادة\" ذاتها في النص.\n"
    "  لا تضع اسم الولاية (الوارد بعد كلمة \"ولاية\") في أي من هذه الحقول الثلاثة أبدًا. "
    "إن لم يُذكر أحد هذه المستويات صراحة أعد له القيمة \"غير مذكور\" بدل اختلاق قيمة أو "
    "إعادة استعمال قيمة حقل آخر. أعد اسم العلم فقط دون تكرار الكلمة الدالة عليه (مثال: أعد "
    "\"الحرايرية\" وليس \"معتمدية الحرايرية\")، ودون دمج عدة إشارات متفرقة في قيمة واحدة.\n\n"
    "- الأطراف: أدرج في \"السائقون\" فقط الأشخاص الذين كانوا يقودون/يقوم بالسياقة فعليًا وقت "
    "الحادث. لا تُدرج مالك المركبة كسائق إن لم يكن هو من يقودها، ولا تضع نصًا وصفيًا (مثل "
    "ملكية المركبة) في حقل \"الرخصة\" — اتركه فارغًا إن لم يرد رقم رخصة أو بطاقة تعريف صريح.\n\n"
    "- تفاصيل_الحادث: \"حالة_الطريق\" تصف الحالة الفيزيائية لسطح الطريق وقت الحادث فقط (مثل: "
    "مبلل، جاف، متضرر، مظلم، وجود عوائق أو مواد منزلقة) — إن لم يرد أي وصف لحالة الطريق في "
    "النص أعد القيمة \"غير محدد\"، ولا تكرر فيها تصنيف نوع الطريق. أما \"نوع_الطريق\" فحدده "
    "باختيار الأقرب دلاليًا من الفئات المتاحة في المخطط (طرق وطنية/جهوية/محلية/مسالك "
    "فلاحية/طرق أخرى/طرق صغرى غير مرقّمة).\n\n"
    "أعد النتيجة ككائن JSON مطابق للمخطط المطلوب فقط."
)


def extract_details(event_summary: str, subject: str, reference: str = None) -> dict:
    log(f"[extract] reference={reference} model={EXTRACTION_MODEL}")
    # نص الحدث/عنوان الحدث come first, identical to classify_subcategory()'s prefix,
    # so Ollama can reuse the KV-cache prefill across both calls for this event.
    prompt = (
        f"نص الحدث:\n{event_summary}\n\n"
        f"عنوان الحدث: {subject}\n\n"
        f"{EXTRACTION_INSTRUCTIONS}"
    )
    return ollama_chat_json(EXTRACTION_MODEL, prompt, EXTRACTION_SCHEMA)


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
        "عنوان": event.get("subject"),  # kept as-is, not LLM-derived
        "كلمات_مفتاحية": extraction.get("كلمات_مفتاحية", []),
        "الموقع": {
            "العنوان": event.get("event_place"),  # kept as-is, not LLM-derived
            "المنطقة": extraction.get("الموقع", {}).get("المنطقة"),
            "المعتمدية": extraction.get("الموقع", {}).get("المعتمدية"),
            "العمادة": extraction.get("الموقع", {}).get("العمادة"),
        },
        "الأطراف": extraction.get("الأطراف", {}),
        "تفاصيل_الحادث": extraction.get("تفاصيل_الحادث", {}),
        "النص_الأصلي": event.get("event_summary"),
    }


def process_event(event: dict, subcategories: list):
    summary = (event.get("event_summary") or "").strip()
    if not summary:
        log(f"[skip] reference={event.get('reference')} has empty event_summary")
        return None

    reference = event.get("reference")
    subject = event.get("subject") or ""
    log(f"[classify] reference={reference} model={CLASSIFICATION_MODEL}")
    subcategory = classify_subcategory(summary, subject, subcategories)

    extraction = extract_details(summary, subject, reference=reference)

    return build_event_record(event, subcategory, extraction)


def main():
    parser = argparse.ArgumentParser(description="Classify & extract traffic events via Ollama")
    parser.add_argument("--limit", type=int, default=None, help="process only the first N events")
    args = parser.parse_args()

    subcategories = load_subcategories(SUBCATEGORY_FILE, CATEGORY)
    events = fetch_events()
    log(f"[data] fetched {len(events)} event(s), start={START_DATE} category={CATEGORY}")
    events = dedupe_events(events)

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
        print(json.dumps(record, ensure_ascii=False, indent=2), flush=True)
        print(flush=True)


if __name__ == "__main__":
    main()
