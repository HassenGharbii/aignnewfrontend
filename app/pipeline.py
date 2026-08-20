"""Classify a traffic event into a sub-category (subcategory.txt) then extract
structured fields from event_summary using Ollama. event_place and subject are
copied verbatim from the source event, never re-derived by the model.
"""

import json
import re

import requests

from . import config


def log(*args):
    print(*args, flush=True)


# ---------------------------------------------------------------------------
# Reference data
# ---------------------------------------------------------------------------
_CATEGORY_BLOCK_RE = re.compile(r'"([^"]+)"\s*:\s*\[(.*?)\]', re.DOTALL)
_STRING_RE = re.compile(r'"([^"]+)"')


def load_subcategories(path, category):
    """subcategory.txt is a loose (trailing-comma) JSON fragment, so it is parsed
    with regex instead of json.loads."""
    text = path.read_text(encoding="utf-8")
    for match in _CATEGORY_BLOCK_RE.finditer(text):
        if match.group(1) == category:
            return _STRING_RE.findall(match.group(2))
    raise ValueError(f"category {category!r} not found in {path}")


# ---------------------------------------------------------------------------
# Ollama calls (raw REST API, so this works regardless of the ollama pip client version)
# ---------------------------------------------------------------------------
def ollama_chat_json(model: str, prompt: str, schema: dict) -> dict:
    url = f"{config.OLLAMA_HOST}/api/chat"
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "format": schema,
        "stream": False,
        "options": {"temperature": 0},
    }
    resp = requests.post(url, json=payload, timeout=config.OLLAMA_TIMEOUT)
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
        "صنّف نص الحدث التالي ضمن إحدى الفئات الفرعية المتاحة فقط، واختر الأقرب دلاليًا لمضمون النص.\n"
        "اعتمد في اختيارك على \"نتيجة الحادث\" الفعلية (وجود إصابات بدنية، وفيات، حريق...) "
        "وليس على \"الأسباب المحتملة\" المذكورة عادة في نهاية النص (مثل وجود زيت أو مواد على "
        "الطريق) — هذه الأسباب لا تُصنَّف كحدث بيئي إلا إذا لم ينتج عنها حادث فعلي بمركبة.\n\n"
        "الفئات الفرعية المتاحة:\n" + "\n".join(f"- {c}" for c in subcategories) + "\n\n"
        f"نص الحدث:\n{event_summary}\n\n"
        "أعد فقط كائن JSON بالصنف الفرعي المختار (بنفس الصياغة الحرفية من القائمة أعلاه) ونسبة ثقة بين 0 و1."
    )
    return ollama_chat_json(config.CLASSIFICATION_MODEL, prompt, schema)


ROAD_TYPES = [
    "طرق وطنية",
    "طرق جهوية",
    "طرق محلية",
    "مسالك فلاحية",
    "طرق أخرى",
    "طرق صغرى غير مرقّمة",
]

# Extraction is split into one schema section per Ollama call instead of one big
# combined schema: a single request covering every nested object builds a large
# constrained-decoding grammar, which is slow (and on small models, unreliable).
# Asking for one section at a time keeps every call small, fast, and accurate.
#
# الضحايا (a nested array-of-count objects) was dropped entirely: across every
# variant tried it produced garbage (16-digit numbers, then bounded-but-still-wrong
# numbers, then an empty list) while تفاصيل_الحادث.عدد_الإصابات/عدد_الوفيات were
# reliably correct in every single test. Those two flat integer fields are now the
# only source of truth for casualty counts.
EXTRACTION_SECTIONS = {
    "كلمات_مفتاحية": {
        "type": "object",
        "properties": {
            "كلمات_مفتاحية": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["كلمات_مفتاحية"],
    },
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
        },
        "required": ["السائقون"],
    },
    "تفاصيل_الحادث": {
        "type": "object",
        "properties": {
            "نوع_الحادث": {"type": "string"},
            "عدد_المركبات": {"type": "integer", "minimum": 0, "maximum": 50},
            "عدد_الإصابات": {"type": "integer", "minimum": 0, "maximum": 200},
            "عدد_الوفيات": {"type": "integer", "minimum": 0, "maximum": 200},
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
}


SECTION_HINTS = {
    "كلمات_مفتاحية": (
        "أعد 3 إلى 6 عبارات قصيرة (كلمة إلى 4 كلمات) تمثل كيانات أو مواضيع رئيسية في النص "
        "(مثال: نوع المركبة، سبب الحادث، الجهة المتدخلة)، وليست جملًا كاملة أو نسخًا من النص."
    ),
    "الموقع": (
        "استخرج ثلاثة مستويات منفصلة بالارتباط الحرفي بكلمتها الدالة في النص، ولا تخمّن قيمة "
        "لمستوى لم يُذكر صراحة:\n"
        "- المنطقة: الاسم الوارد بعد كلمة \"حي\" أو \"منطقة\".\n"
        "- المعتمدية: الاسم الوارد بعد كلمة \"معتمدية\" حرفيًا فقط.\n"
        "- العمادة: الاسم الوارد بعد كلمة \"عمادة\" حرفيًا فقط — لا تضع فيها اسم الولاية أو "
        "المعتمدية أو المنطقة إن لم تَرِد كلمة \"عمادة\" ذاتها في النص.\n"
        "لا تضع اسم الولاية (الوارد بعد كلمة \"ولاية\") في أي من هذه الحقول الثلاثة أبدًا. "
        "إن لم يُذكر أحد هذه المستويات صراحة في النص أعد له القيمة \"غير مذكور\" بدل اختلاق "
        "قيمة أو إعادة استعمال قيمة حقل آخر. أعد اسم العلم فقط دون تكرار الكلمة الدالة عليه "
        "(مثال: أعد \"الحرايرية\" وليس \"معتمدية الحرايرية\")، ودون دمج عدة إشارات متفرقة "
        "من النص في قيمة واحدة."
    ),
    "الأطراف": (
        "أدرج في \"السائقون\" فقط الأشخاص الذين كانوا يقودون/يقوم بالسياقة فعليًا وقت الحادث. "
        "لا تُدرج مالك المركبة كسائق إن لم يكن هو من يقودها، ولا تضع نصًا وصفيًا (مثل ملكية "
        "المركبة) في حقل \"الرخصة\" — اتركه فارغًا إن لم يرد رقم رخصة أو بطاقة تعريف صريح.\n"
        "تنبيه هام: عبارة \"ابن [اسم الأب] و المسماة [اسم الأم]\" (أو \"ابنة ...\") تصف نسب "
        "الشخص (تذكر اسم أمه للتعريف بهويته) وليست شخصًا إضافيًا حاضرًا في الحادث — لا تُدرج "
        "اسم الأم أو الأب المذكورين بهذه الصيغة كسائق أو كطرف منفصل بأي حال."
    ),
    "تفاصيل_الحادث": (
        "\"حالة_الطريق\" تصف الحالة الفيزيائية لسطح الطريق وقت الحادث فقط (مثل: مبلل، "
        "جاف، متضرر، مظلم، وجود عوائق أو مواد منزلقة) — إن لم يرد أي وصف لحالة الطريق في "
        "النص أعد القيمة \"غير محدد\"، ولا تكرر فيها تصنيف نوع الطريق. "
        "أما \"نوع_الطريق\" فحدده باختيار الأقرب دلاليًا من الفئات المتاحة في المخطط "
        "(طرق وطنية/جهوية/محلية/مسالك فلاحية/طرق أخرى/طرق صغرى غير مرقّمة).\n"
        "\"عدد_الإصابات\" و\"عدد_الوفيات\" يجب أن يكونا دقيقين: إن ذُكر عددهما صراحة في قسم "
        "\"نتيجة الحادث\" استعمله كما هو حرفيًا. إن لم يُذكر رقم صريح، عُدّ فقط الأشخاص "
        "المذكورين بالاسم بصفتهم مصابين أو متوفين فعليًا في نتيجة الحادث — لا تحتسب السائقين "
        "غير المصابين، ولا الشهود، ولا الأب/الأم المذكورين ضمن نسب شخص آخر للتعريف بهويته."
    ),
}


def extract_details(event_summary: str, subject: str, reference: str = None) -> dict:
    result = {}
    for section_name, section_schema in EXTRACTION_SECTIONS.items():
        log(f"[extract:{section_name}] reference={reference} model={config.EXTRACTION_MODEL}")
        hint = SECTION_HINTS.get(section_name)
        prompt = (
            "أنت محلل بيانات لأحداث المرور. استخرج حصرًا الحقل التالي من النص أدناه بدقة، "
            "دون اختلاق معلومات غير موجودة فيه.\n\n"
            f"الحقل المطلوب: {section_name}\n"
            + (f"{hint}\n" if hint else "")
            + f"\nعنوان الحدث: {subject}\n\n"
            f"نص الحدث:\n{event_summary}\n\n"
            "أعد النتيجة ككائن JSON مطابق للمخطط المطلوب فقط."
        )
        result[section_name] = ollama_chat_json(config.EXTRACTION_MODEL, prompt, section_schema)
    return result


# ---------------------------------------------------------------------------
# Assembling the final record (schemaextractevent.txt)
# ---------------------------------------------------------------------------
def build_event_record(event: dict, subcategory: dict, extraction: dict) -> dict:
    return {
        "معرف_الحدث": event.get("reference"),
        "المصدر": event.get("source"),
        "الطوابع_الزمنية": {
            "وقت_الإنشاء": None,
            "وقت_التحديث": None,
            "وقت_الحدث": event.get("time"),
        },
        "التصنيف": {
            "الصنف_الرئيسي": config.CATEGORY,
            "الصنف_الفرعي": subcategory.get("الصنف_الفرعي"),
            "نسبة_الثقة": subcategory.get("نسبة_الثقة"),
        },
        "عنوان": event.get("subject"),  # kept as-is, not LLM-derived
        "كلمات_مفتاحية": extraction.get("كلمات_مفتاحية", {}).get("كلمات_مفتاحية", []),
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
    log(f"[classify] reference={reference} model={config.CLASSIFICATION_MODEL}")
    subcategory = classify_subcategory(summary, subcategories)

    extraction = extract_details(summary, event.get("subject") or "", reference=reference)

    return build_event_record(event, subcategory, extraction)
