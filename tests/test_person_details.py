from app.person_details import person_details

REPORT = (
    "ملخص الحدث : اليـوم 23-11-2026 الساعة 0200 جد حادث مرور . الدراجة النارية : نوع فورزا "
    "رقم هيكلها sample0000000001 على ملك سائقها المدعو سامي بن علي الهادي التجريبي تونسي "
    "مولود في 14-7-2002 مهنته متربص بالتكوين المهني صاحب ب ت و 11111111 يرافقه شقيقه "
    "المدعو/ أيمن التجريبي تونسي مولود في 27-5-2004 تلميذ بمعهد خاص صاحب ب ت و 22222222 "
    "السيارة الخاصة : نوع رينو رقم 1000 تونس 100 على ملك سائقها المدعو/ كمال بن صالح "
    "عمر المثال تونسي مولود في 03-7-1978 مهنته عسكري ضابط صف رتبته وكيل رقم التجنيد 10000/90 "
    "يعمل بالوحدة صاحب ب ت و 33333333 صاحب رخصة سياقة رقم 45678/21 بتاريخ 29-5-2010 "
    "ترافقه على متنها زوجته المسماة/ سعاد بنت أحمد المثال"
)


def test_reads_cin_birth_and_occupation_for_first_driver():
    d = person_details(REPORT, "سامي بن علي الهادي", "2026-11-23T02:00:00")
    assert d == {
        "cin": "11111111",
        "license": None,
        "gender": "male",
        "age_range": "24 سنة",
        "occupation": "متربص بالتكوين المهني",
    }


def test_does_not_borrow_companion_details():
    # The first driver's segment ends at "يرافقه", so the companion's CIN must not leak in.
    d = person_details(REPORT, "سامي بن علي الهادي")
    assert d["cin"] == "11111111"


def test_second_driver_with_license_and_slash_name_marker():
    d = person_details(REPORT, "كمال بن صالح عمر المثال", "2026-11-23")
    assert d["cin"] == "33333333"
    assert d["license"] == "45678/21"
    assert d["age_range"] == "48 سنة"
    assert d["occupation"] == "عسكري ضابط صف"


def test_female_and_missing_event_date():
    text = "المدعوة منى بن سالم مولودة في 1-2-1990 صاحبة ب.ت.و 44444444"
    d = person_details(text, "منى بن سالم")
    assert d["gender"] == "female"
    assert d["age_range"] == "مواليد 1990"
    assert d["cin"] == "44444444"


def test_name_not_in_text_returns_empty():
    d = person_details(REPORT, "شخص غير موجود")
    assert all(v is None for v in d.values())
