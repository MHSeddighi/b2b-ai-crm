"""Persian labels + deterministic reason translator for the API layer.

The deterministic engine keeps its canonical English reason strings internally
(the MCP contract and engine tests rely on them); this module maps them to
plain Persian at the API boundary, so every user-facing surface — dashboard,
customer 360, analyses, and the LLM summary snapshot — is fully Persian.
"""
from __future__ import annotations

import re
from typing import Any, Callable

# ---------------------------------------------------------------------------
# Label maps
# ---------------------------------------------------------------------------
SIGNAL_FA = {
    "profit": "سودآوری",
    "purchase_trend": "روند خرید",
    "payment_behavior": "رفتار پرداخت",
    "share_of_wallet": "سهم از خرید مشتری",
    "purchase_cycle": "چرخه خرید",
    "margin_trend": "روند حاشیه سود",
    "offer_affinity": "پاسخ به پیشنهادها",
    "complaint_impact": "اثر شکایات",
    "dev_request": "درخواست‌های توسعه",
    "growth_potential": "پتانسیل رشد",
    "churn_risk": "ریسک از دست دادن مشتری",
}

STATUS_FA = {
    "positive": "مثبت",
    "neutral": "خنثی",
    "warning": "هشدار",
    "critical": "بحرانی",
    "unknown": "نامشخص",
    "low_confidence": "کم‌اطمینان",
    "high": "بالا",
    "medium": "متوسط",
    "low": "کم",
    "poor": "ضعیف",
    "healthy": "سالم",
    "good": "خوب",
    "declining": "رو به کاهش",
    "improving": "در حال بهبود",
    "stable": "پایدار",
}

DIRECTION_FA = {
    "improving": "در حال بهبود",
    "stable": "پایدار",
    "declining": "رو به کاهش",
    "neutral": "خنثی",
    "unknown": "نامشخص",
}

SEVERITY_FA = {
    "critical": "بحرانی",
    "high": "زیاد",
    "warning": "متوسط",
    "neutral": "خنثی",
    "low": "کم",
    "positive": "مثبت",
}

ACTION_FA = {
    "RETENTION_CALL": "تماس برای حفظ مشتری",
    "SERVICE_RECOVERY": "رسیدگی به شکایت‌ها",
    "ACCOUNT_REVIEW": "بازبینی حساب مشتری",
    "CROSS_SELL": "فروش محصول‌های مکمل",
    "UPSELL": "افزایش حجم فروش",
    "REACTIVATION": "بازگرداندن مشتری از دست‌رفته",
    "PRICE_REVIEW": "بازبینی قیمت‌گذاری",
    "DISCOUNT_REDUCTION": "کاهش وابستگی به تخفیف",
    "PAYMENT_TERMS_REVIEW": "بازبینی شرایط پرداخت",
    "CREDIT_REVIEW": "بازبینی اعتبار مشتری",
    "LOYALTY_OFFER": "پیشنهاد وفاداری",
    "VOLUME_OFFER": "پیشنهاد حجمی",
    "BUNDLE_OFFER": "پیشنهاد ترکیبی محصول‌ها",
    "PRODUCT_DEVELOPMENT_FOLLOWUP": "پیگیری درخواست توسعه محصول",
    "NO_ACTION": "فقط پایش",
}

# Recommendation "systems" — the groups the customer-360 page shows side by
# side (product/sales offers, retention, quality, commercial, collection...).
ACTION_CATEGORY_FA = {
    "relationship": "حفظ و رابطه",
    "quality": "کیفیت و شکایت",
    "sales": "فروش و رشد",
    "commercial": "مالی و قرارداد",
    "collection": "وصول و اعتبار",
    "attention": "پایش",
}

ACTION_NEXT_STEP_FA = {
    "RETENTION_CALL": "نماینده فروش برای درک دلیل کاهش خرید و بازگرداندن مشتری تماس بگیرد.",
    "SERVICE_RECOVERY": "شکایت را حل کنید و پیش از هر فروش جدید، رضایت مشتری را مطمئن شوید.",
    "ACCOUNT_REVIEW": "جلسه بازبینی حساب برای ارزیابی دوباره رابطه و برنامه آینده برگزار کنید.",
    "CROSS_SELL": "با توجه به رابطه سالم و ظرفیت خرید، خانواده محصول مرتبط را پیشنهاد دهید.",
    "UPSELL": "حجم یا نسخه‌های بهتر محصولاتی را که مشتری قبلاً خریده، پیشنهاد دهید.",
    "REACTIVATION": "با مشتری‌ای که خیلی از چرخه عادی خریدش گذشته تماس بگیرید و دوباره جذبش کنید.",
    "PRICE_REVIEW": "قیمت‌گذاری یا ساختار هزینه را برای مشتری با حاشیه سود پایین بازبینی کنید.",
    "DISCOUNT_REDUCTION": "برای مشتری حساس به تخفیف با حاشیه سود کم، سطح تخفیف را کاهش دهید.",
    "PAYMENT_TERMS_REVIEW": "شرایط پرداخت را با مشتری‌ای که پرداختش به تأخیر افتاده بازبینی کنید.",
    "CREDIT_REVIEW": "سقف اعتبار و ریسک مطالبات را برای مشتری پرریسک بازبینی کنید.",
    "LOYALTY_OFFER": "برای تقویت رابطه قوی، پیشنهاد وفاداری بدهید.",
    "VOLUME_OFFER": "برای افزایش سهم از خرید، مشوق حجمی پیشنهاد دهید.",
    "BUNDLE_OFFER": "محصول‌های مکمل را برای مشتری پاسخ‌گو به پیشنهاد ترکیب کنید.",
    "PRODUCT_DEVELOPMENT_FOLLOWUP": "درخواست توسعه باز مشتری را پیگیری کنید.",
    "NO_ACTION": "اقدامی لازم نیست؛ فقط وضعیت را پایش کنید.",
}


# ---------------------------------------------------------------------------
# Persian number formatting
# ---------------------------------------------------------------------------
def fa_num(value: Any) -> str:
    if value is None:
        return "نامشخص"
    try:
        fv = float(value)
    except (TypeError, ValueError):
        return str(value)
    digits = "۰۱۲۳۴۵۶۷۸۹"
    s = f"{fv:,.0f}" if fv == int(fv) else f"{fv:,.1f}"
    return "".join(digits[int(ch)] if ch.isdigit() else ch for ch in s)


def fa_pct(value: Any) -> str:
    """Fraction (0..1) -> Persian percent string."""
    if value is None:
        return "نامشخص"
    try:
        fv = float(value)
    except (TypeError, ValueError):
        return str(value)
    return fa_num(round(fv * 100)) + "٪"


def fa_money(value: Any) -> str:
    if value is None:
        return "نامشخص"
    try:
        fv = float(value)
    except (TypeError, ValueError):
        return str(value)
    return fa_num(round(fv)) + " تومان"


def _percent(raw: str) -> str:
    """'73.0' or '73.0%' or '-100%' -> '۷۳٪' / '۱۰۰٪'. The sign is dropped:
    the surrounding Persian text already conveys direction (کاهش/افزایش)."""
    try:
        fv = float(str(raw).rstrip("%"))
    except (TypeError, ValueError):
        return str(raw)
    return fa_num(abs(fv)) + "٪"


def _number(raw: str) -> str:
    try:
        if raw.endswith("%"):
            return fa_num(float(raw[:-1])) + "٪"
        return fa_num(float(raw.replace(",", "")))
    except ValueError:
        return raw


def _months_source(text: str) -> str:
    """'3 month(s), source: X' -> '۳ ماه، منبع: X'."""
    out = text
    m = re.match(r"(\d+) month\(s\), source: (.+)", text.strip())
    if m:
        out = f"{_number(m.group(1))} ماه، منبع: {m.group(2)}"
    return out.replace("source:", "منبع:")


_OFFER_TYPE_FA = {
    "discount": "تخفیفی",
    "price": "قیمتی",
    "volume": "حجمی",
    "volume_offer": "حجمی",
    "payment_terms": "مدت‌دار",
    "duration": "مدت‌دار",
    "bundle": "ترکیبی",
    "regular": "عادی",
    "standard": "استاندارد",
    "other": "سایر",
}


def _offer_type(raw: str) -> str:
    return _OFFER_TYPE_FA.get(raw.strip().lower(), raw)


# ---------------------------------------------------------------------------
# Deterministic reason translator
# ---------------------------------------------------------------------------
# Ordered (pattern, replacement) rules. Numbers/percent signs are reformatted
# to Persian; the surrounding text is rewritten to plain Persian.
_PLAIN: dict[str, str] = {
    "Cannot compute cycle deviation": "امکان محاسبه انحراف چرخه خرید نیست",
    "Complaint impact warning": "هشدار اثر شکایت",
    "Customer has strong purchase activity": "مشتری خرید فعال و پایداری دارد",
    "Customer remains profitable": "مشتری همچنان سودآور است",
    "External total-spend estimate is zero/missing": "برآورد کل خرید مشتری موجود نیست",
    "Insufficient cost-matched sales to compute margin trend": "داده کافی برای محاسبه روند حاشیه سود نیست",
    "Insufficient distinct purchase dates": "تاریخ خرید کافی برای تحلیل نیست",
    "Insufficient history: no comparable previous period": "تاریخچه کافی برای مقایسه با دوره قبل نیست",
    "Insufficient offer history to infer preference": "تاریخچه پیشنهاد کافی برای تشخیص ترجیح نیست",
    "Insufficient order history to establish a trend": "تاریخچه سفارش کافی برای تشخیص روند نیست",
    "Insufficient purchase history for cycle analysis": "تاریخچه خرید کافی برای تحلیل چرخه نیست",
    "No collection / payment records available": "سابقه پرداخت و وصولی در دسترس نیست",
    "No complaints on record": "شکایتی ثبت نشده است",
    "No external wallet-share estimate available": "برآورد خارجی سهم از خرید در دسترس نیست",
    "No offer response history available": "سابقه پاسخ به پیشنهاد در دسترس نیست",
    "No pre-complaint purchase baseline to compare": "مبنای خرید قبل از شکایت در دسترس نیست",
    "No sales revenue available": "درآمد فروشی در دسترس نیست",
    "Payment behaviour deteriorating": "رفتار پرداخت رو به وخامت است",
    "Payment behaviour is healthy": "رفتار پرداخت سالم است",
    "Payment behaviour critical": "رفتار پرداخت بحرانی است",
    "Purchase volume declined significantly": "حجم خرید به‌طور قابل توجهی کاهش یافته",
    "Purchase volume declining": "حجم خرید در حال کاهش است",
    "Required cost data is unavailable": "داده هزینه مورد نیاز در دسترس نیست",
    "Severe complaint impact": "اثر شدید شکایت",
    "Customer is far beyond normal purchase cycle": "مشتری خیلی فراتر از چرخه عادی خرید است",
    "Customer is beyond normal purchase cycle": "مشتری فراتر از چرخه عادی خرید است",
    "Complaint activity followed by purchase decline": "پس از شکایت، خرید کاهش یافته",
    "Share of wallet is low": "سهم از خرید مشتری پایین است",
    "negative_profit": "سودآوری منفی",
    "Wallet-share estimate is stale": "برآورد سهم از خرید قدیمی است",
    "Insufficient wallet data": "داده سهم از خرید کافی نیست",
}

_PATTERNS: list[tuple[re.Pattern, Callable[[re.Match], str]]] = [
    # long-form first (more specific patterns before short ones)
    (re.compile(r"Customer is (\d+) days since last purchase vs a normal cycle of ([\d.]+) days \(ratio [\d.]+\)"),
     lambda m: f"{_number(m.group(1))} روز از آخرین خرید گذشته در حالی که چرخه عادی خرید {_number(m.group(2))} روز است"),
    (re.compile(r"Customer responds best to (.+?) offers \((\d+) accepted / (\d+) rejected\)"),
     lambda m: f"مشتری بیشتر به پیشنهادهای «{_offer_type(m.group(1))}» پاسخ می‌دهد ({_number(m.group(2))} قبول / {_number(m.group(3))} رد)"),
    (re.compile(r"Estimated share of wallet is only ([\d.]+%) \((.+)\)$"),
     lambda m: f"سهم از خرید مشتری تنها {_percent(m.group(1))} است ({_months_source(m.group(2))})"),
    (re.compile(r"Share of wallet is only ([\d.]+%) \((.+)\)$"),
     lambda m: f"سهم از خرید مشتری تنها {_percent(m.group(1))} است ({_months_source(m.group(2))})"),
    (re.compile(r"Share of wallet is ([\d.]+%) \((.+)\)$"),
     lambda m: f"سهم از خرید مشتری {_percent(m.group(1))} است ({_months_source(m.group(2))})"),
    (re.compile(r"(\d+)/(\d+) payments are late"),
     lambda m: f"{_number(m.group(1))} از {_number(m.group(2))} پرداخت با تأخیر بوده است"),
    (re.compile(r"(\d+) unresolved complaint\(s\) remain"),
     lambda m: f"{_number(m.group(1))} شکایت باز مانده است"),
    (re.compile(r"(\d+) unresolved complaint\(s\)"),
     lambda m: f"{_number(m.group(1))} شکایت باز"),
    (re.compile(r"(\d+) bounced cheque\(s\)"),
     lambda m: f"{_number(m.group(1))} چک برگشتی"),
    (re.compile(r"(\d+) open development request\(s\)"),
     lambda m: f"{_number(m.group(1))} درخواست توسعه باز"),
    (re.compile(r"Payment delay increased from ([\d.]+) to ([\d.]+) days"),
     lambda m: f"میانگین تأخیر پرداخت از {_number(m.group(1))} به {_number(m.group(2))} روز افزایش یافته"),
    (re.compile(r"Profit margin is ([\d.]+%) but cost data covers only ([\d.]+%) of revenue, so it is not reliable"),
     lambda m: f"حاشیه سود {_percent(m.group(1))} است اما داده هزینه فقط {_percent(m.group(2))} از درآمد را پوشش می‌دهد؛ بنابراین قابل اتکا نیست"),
    (re.compile(r"Profit margin is ([\d.]+%) \(cost coverage ([\d.]+%)\)"),
     lambda m: f"حاشیه سود {_percent(m.group(1))} است (پوشش هزینه {_percent(m.group(2))})"),
    (re.compile(r"Profit margin ([\d.]+%)"),
     lambda m: f"حاشیه سود {_percent(m.group(1))}"),
    (re.compile(r"Purchase decline \(([+-]?[\d.]+%)\) followed the complaint"),
     lambda m: f"پس از شکایت، خرید {_percent(m.group(1))} کاهش یافته"),
    (re.compile(r"Revenue changed ([+-]?[\d.]+%) \((\d+) vs (\d+) orders\)"),
     lambda m: f"درآمد {_percent(m.group(1))} تغییر کرده ({_number(m.group(2))} در برابر {_number(m.group(3))} سفارش)"),
    (re.compile(r"\((\d+) vs (\d+) orders\)"),
     lambda m: f"({_number(m.group(1))} در برابر {_number(m.group(2))} سفارش)"),
    (re.compile(r"Margin moved from ([\d.]+%) to ([\d.]+%)"),
     lambda m: f"حاشیه سود از {_percent(m.group(1))} به {_percent(m.group(2))} تغییر کرده"),
    (re.compile(r"Total revenue ([\d,]+)"),
     lambda m: f"درآمد کل {_number(m.group(1))}"),
    (re.compile(r"Wallet estimate is (\d+) days old"),
     lambda m: f"برآورد سهم از خرید {_number(m.group(1))} روز قدیمی است"),
    (re.compile(r"No recovery after (\d+) days"),
     lambda m: f"{_number(m.group(1))} روز بدون بهبود"),
    (re.compile(r"\(change ([+-]?[\d.]+%)\)"),
     lambda m: f"(تغییر {_percent(m.group(1))})"),
    (re.compile(r"\(cost coverage ([\d.]+%)\)"),
     lambda m: f"(پوشش هزینه {_percent(m.group(1))})"),
]


def translate_reason(text: str) -> str:
    """Translate one engine reason string to plain Persian.

    Every matching rule is applied (a reason can combine several fragments);
    unknown fragments are left unchanged — the translator never corrupts.
    """
    if not text:
        return text
    out = text
    for _ in range(4):
        changed = False
        for pattern, repl in _PATTERNS:
            if pattern.search(out):
                out = pattern.sub(repl, out)
                changed = True
        if not changed:
            break
    return _PLAIN.get(out, out)


def translate_reasons(reasons: list[str]) -> list[str]:
    return [translate_reason(r) for r in reasons]


def action_name(action_id: str, fallback: str = "") -> str:
    return ACTION_FA.get(action_id, fallback or action_id)


def action_next_step(action_id: str, fallback: str = "") -> str:
    return ACTION_NEXT_STEP_FA.get(action_id, fallback)


def status_fa(status: str) -> str:
    return STATUS_FA.get(status, status)


def direction_fa(direction: str) -> str:
    return DIRECTION_FA.get(direction, direction)
