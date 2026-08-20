"""Mirrors src/data/governorates.ts so the backend computes the exact same
canonical governorate name the frontend would derive client-side — otherwise
filtering by region server-side and displaying by region client-side disagree.
"""

GOVERNORATES = [
    "أريانة", "باجة", "بن عروس", "بنزرت", "قابس", "قفصة", "جندوبة", "القيروان",
    "القصرين", "قبلي", "الكاف", "المهدية", "منوبة", "مدنين", "المنستير", "نابل",
    "صفاقس", "سيدي بوزيد", "سليانة", "سوسة", "تطاوين", "توزر", "تونس", "زغوان",
]


def _normalize(s: str) -> str:
    # Informal Arabic text often swaps the ة/ه ending (e.g. "منوبه" for "منوبة").
    return s.replace("ة", "ه")


def match_governorate(*texts) -> str | None:
    """Best-effort match of free-text candidates against a governorate name,
    checked in the given priority order. Returns the canonical Arabic name."""
    for text in texts:
        if not text:
            continue
        haystack = _normalize(text)
        for name in GOVERNORATES:
            if _normalize(name) in haystack:
                return name
    return None
