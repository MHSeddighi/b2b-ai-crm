"""Tests for the deterministic Persian ZWNJ (نیمفاصله) fixer."""
from backend.agents.persian import fix_persian_zwnj


def test_user_reported_examples():
    """The exact stuck-word cases the user reported must be fixed."""
    cases = {
        "حلنشده": "حل\u200cنشده",
        "جلسهی": "جلسه\u200cی",
        "یکییکی": "یکی\u200cیکی",
        "مشتریها": "مشتری\u200cها",
        "مشتریهایی": "مشتری\u200cهایی",
        "بهاحتمال": "به\u200cاحتمال",
        "پرارزش": "پر\u200cارزش",
        "میشود": "می\u200cشود",
        "میکنند": "می\u200cکنند",
        "گرفتهاند": "گرفته\u200cاند",
        "نشدهاند": "ن\u200cشده\u200cاند",
        "نقطهی": "نقطه\u200cی",
        "چرخهی": "چرخه\u200cی",
        "ادامهی": "ادامه\u200cی",
        "سابقهایشان": "سابقه\u200cایشان",
        "توسعهای": "توسعه\u200cای",
    }
    for raw, expected in cases.items():
        assert fix_persian_zwnj(raw) == expected, f"{raw!r} -> {fix_persian_zwnj(raw)!r}"


def test_real_words_never_corrupted():
    """Words where ZWNJ must NOT be inserted stay untouched."""
    guards = [
        "میز", "میوه", "میدان", "ماهی", "رها", "بها", "شاه", "چاه",
        "سلام", "تهی", "میانگین", "میهمان",
    ]
    for word in guards:
        assert fix_persian_zwnj(word) == word, f"{word!r} corrupted"


def test_non_persian_untouched():
    assert fix_persian_zwnj("hello world") == "hello world"
    assert fix_persian_zwnj("C_117580") == "C_117580"
    assert fix_persian_zwnj("SELECT * FROM sales") == "SELECT * FROM sales"
    assert fix_persian_zwnj("") == ""


def test_full_paragraph():
    """A realistic paragraph with several compound words is fixed in one pass."""
    raw = (
        "این مشتریها مدتهاست خرید نکردهاند و شکایتهای باز دارند. "
        "بهاحتمال زیاد برای همیشه از دست میروند؛ یک جلسهی اختصاصی "
        "برای ادامهی همکاری بگذارید."
    )
    out = fix_persian_zwnj(raw)
    assert "مشتری\u200cها" in out
    assert "ن\u200cکرده\u200cاند" in out
    assert "شکایت\u200cهای" in out
    assert "به\u200cاحتمال" in out
    assert "می\u200cروند" in out
    assert "جلسه\u200cی" in out
    assert "ادامه\u200cی" in out


def test_idempotent():
    """Running the fixer twice changes nothing the second time."""
    raw = "مشتریها حلنشده جلسهی یکییکی"
    once = fix_persian_zwnj(raw)
    twice = fix_persian_zwnj(once)
    assert once == twice
