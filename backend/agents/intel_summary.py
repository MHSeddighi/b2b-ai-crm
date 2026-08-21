"""LLM-generated intelligence summaries (cached, deterministic context).

The summary is the only place the LLM writes user-facing prose for the 360
view and the dashboard: it receives a compact, backend-computed snapshot of the
customer (signals, state, reasons, actions, counts, recent records) and turns it
into plain-language Persian guidance for a sales manager — never scores,
algorithms or backend jargon.

Results are cached to disk keyed by the fingerprint of the deterministic
snapshot (see backend.crm.cache), so the first computation is the only slow one;
every later visit reads the cached text instantly. A per-key in-flight guard
prevents duplicate LLM calls when the page is opened concurrently.
"""
from __future__ import annotations

import asyncio
from typing import Any, Callable

from backend.agents.db_agent import _llm_call_async
from backend.config import settings
from backend.crm import cache as store
from backend.crm.labels import (
    ACTION_FA,
    ACTION_NEXT_STEP_FA,
    SIGNAL_FA,
    fa_money,
    fa_num,
    fa_pct,
)

_SYSTEM = """تو «خلاصه‌ساز هوشمند» محصول Cust Intel هستی؛ همان دستیار فروش مدیران.

کار تو این است که یک «خلاصه هوشمند» و «پیشنهادهای اقدام» از روی واقعیت‌های
حساب‌شده‌ی پشت صحنه (که به تو داده می‌شود) به زبان ساده و کاملاً فارسی برای
مدیر فروش بنویسی. تو هیچ عددی را محاسبه نمی‌کنی و هیچ تخمینی نمی‌زنی؛ فقط همان
حقایقی را که داده شده به زبان انسانی و قابل‌فهم بیان می‌کنی.

قوانین سخت:
- فقط فارسی روان با نیم‌فاصله‌ی درست بنویس (مثلاً «می‌شود»، «نشده»، «جلسه‌ی»).
- به هیچ وجه از واژه‌های فنی استفاده نکن: امتیاز، الگوریتم، سیگنال، آستانه،
  بک‌اند، مدل، ابزار، اولویت، اطمینان، درصد ریسک عددی، و نام‌های انگلیسی.
- به‌جای «امتیاز ریسک فلان» بگو «وضعیت نگران‌کننده / نیازمند توجه / خوب است».
- خلاصه را در ۳ بخش با عنوان‌های «وضعیت کلی»، «نکات مهم» و «پیشنهاد اقدام»
  بنویس. هر بخش چند جمله‌ی کوتاه؛ جمعاً حداکثر ۱۸۰ کلمه.
- عنوان هر بخش را فقط به‌صورت متن ساده و بدون هیچ علامت مارک‌داون بنویس، مثلاً
  «وضعیت کلی:» — از «###»، «##»، «#» و «**» استفاده نکن. برای موارد فهرستی
  می‌توانی از خط تیره‌ی «-» در ابتدای سطر استفاده کنی.
- پیشنهادها را فقط از فهرست «اقدام‌های پیشنهادی» که داده شده انتخاب کن و
  ساده‌سازی‌شده بنویس؛ هیچ اقدام جدیدی اختراع نکن.
- اعداد را با ارقام فارسی و واحد «تومان» برای پول بنویس.
"""

_NEXT_ACTION_SYSTEM = """تو «دستیار اقدام» محصول Cust Intel هستی؛ همان دستیار فروش مدیران.

کار تو انتخاب و توضیح «اقدام بعدی» اصلی برای یک مشتری است، بر اساس سیگنال‌ها و
اقدام‌های پیشنهادی‌ای که موتور (ابزارهای سامانه) از داده‌ی واقعی محاسبه کرده و به
تو داده می‌شود. تو هیچ عددی را محاسبه نمی‌کنی و هیچ تخمینی نمی‌زنی.

قوانین سخت:
- فقط از سیگنال‌ها و اقدام‌های پیشنهادیِ داده‌شده استفاده کن؛ هیچ عدد، دلیل یا
  اقدامی اختراع نکن.
- یک اقدام اصلی انتخاب کن و آن را با شواهد واقعی (دلایل همان سیگنال‌ها) توضیح بده:
  چرا الان، چه کاری، گام بعدی مشخص.
- فقط فارسی روان با نیم‌فاصله‌ی درست؛ بدون واژه‌ی فنی (امتیاز، سیگنال، الگوریتم،
  بک‌اند، مدل) و بدون نام انگلیسی.
- بدون هیچ علامت مارک‌داون (###، **، و امثال آن)؛ فقط متن ساده.
- خروجی را دقیقاً در همین قالب چهارخطی بنویس (جمعاً حداکثر ۹۰ کلمه):
اقدام اصلی: <نام اقدام>
چرا الان: <یک یا دو شاهد از سیگنال‌ها>
گام بعدی: <یک جمله‌ی عملی و مشخص>
اولویت: <بالا | متوسط | کم>
"""


def _signal_lines(snapshot: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for sig in snapshot.get("signals", []):
        name = sig.get("label") or SIGNAL_FA.get(sig.get("id", ""), sig.get("id", ""))
        detail = sig.get("detail", "")
        parts = [f"{name}: {detail}" if detail else name]
        if sig.get("reasons"):
            parts.append("؛ ".join(sig["reasons"][:2]))
        lines.append(" - " + " ".join(parts))
    return lines


def _action_lines(snapshot: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for a in snapshot.get("actions", [])[:5]:
        name = ACTION_FA.get(a.get("action_id", ""), a.get("name", a.get("action_id", "")))
        reason = a.get("reason", "") or ""
        lines.append(f" - {name} ({reason})")
    return lines


def _customer_snapshot(payload: dict[str, Any]) -> dict[str, Any]:
    """Compact, LLM-friendly snapshot of one customer's deterministic facts,
    built directly from the /360 payload (no extra computation)."""
    cust = payload.get("customer", {})
    offers = payload.get("offers", [])
    collections = payload.get("collections", [])
    return {
        "customer_id": cust.get("Customer_ID") or payload.get("customer_id", ""),
        "segment": cust.get("Customer_Segment") or "نامشخص",
        "status": cust.get("Customer_Status") or "نامشخص",
        "relationship_start": cust.get("Relationship_Start_Date") or "نامشخص",
        "sales_rep": cust.get("Sales_Rep_ID") or "نامشخص",
        "revenue": payload.get("revenue") or 0,
        "orders": payload.get("orders") or 0,
        "avg_order": payload.get("avgOrderValue") or 0,
        "last_purchase": payload.get("lastPurchase") or "نامشخص",
        "complaints_count": payload.get("complaints") or 0,
        "unresolved_complaints": payload.get("unresolvedComplaints") or 0,
        "top_complaints": [
            (r["reason"], r["count"]) for r in payload.get("complaintReasons", [])
        ],
        "interactions_count": payload.get("interactionsCount") or 0,
        "dev_open": payload.get("devOpen") or 0,
        "dev_count": payload.get("devCount") or 0,
        "offers_count": len(offers),
        "offer_acceptance": payload.get("offerAcceptance") or None,
        "best_offer_type": payload.get("bestOfferType") or "نامشخص",
        "overdue_amount": payload.get("overdueAmount") or 0,
        "bounced_checks": payload.get("bouncedChecks") or 0,
        "risk_level": payload.get("riskLevel") or "نامشخص",
        "signals": [
            {
                "id": s.get("id", ""),
                "label": s.get("label", ""),
                "detail": s.get("detail", ""),
                "status": s.get("tone", ""),
                "reasons": s.get("reasons", [])[:2],
            }
            for s in payload.get("riskSignals", [])
        ],
        "actions": [
            {
                "action_id": a.get("id", ""),
                "name": a.get("name", ""),
                "reason": a.get("reason", ""),
            }
            for a in payload.get("actions", [])[:5]
        ],
        "collections_overdue": sum(
            c.get("amount") or 0 for c in collections if (c.get("delay_days") or 0) > 0
        ),
        "bounced_checks_raw": sum(
            1 for c in collections if c.get("bounced") == "بله"
        ),
    }


def _dashboard_snapshot(det: dict[str, Any]) -> dict[str, Any]:
    return {
        "kpis": det.get("kpis", []),
        "at_risk": det.get("intelligence", {}).get("at_risk", {}),
        "complaint_themes": det.get("intelligence", {}).get("complaint_themes", []),
        "offer_effectiveness": det.get("intelligence", {}).get("offer_effectiveness", []),
        "collection_risk": det.get("intelligence", {}).get("collection_risk", {}),
        "winback": det.get("intelligence", {}).get("winback", {}),
        "segment_share": det.get("intelligence", {}).get("segment_share", []),
    }


def _customer_prompt(snapshot: dict[str, Any]) -> str:
    s = snapshot
    lines = [
        f"مشتری: {s['customer_id']}",
        f"بخش بازار: {s['segment']} | وضعیت: {s['status']} | شروع همکاری: {s['relationship_start']} | نماینده فروش: {s['sales_rep']}",
        f"درآمد کل: {fa_money(s['revenue'])} | سفارش‌ها: {fa_num(s['orders'])} | میانگین هر سفارش: {fa_money(s['avg_order'])} | آخرین خرید: {s['last_purchase']}",
        f"شکایت‌ها: {fa_num(s['complaints_count'])} (باز: {fa_num(s['unresolved_complaints'])})",
    ]
    if s["top_complaints"]:
        lines.append("موضوع‌های پرتکرار شکایت: " + "، ".join(
            f"{t} ({fa_num(c)} مورد)" for t, c in s["top_complaints"][:3]))
    lines.append(
        f"تعامل‌ها: {fa_num(s['interactions_count'])} | درخواست توسعه: {fa_num(s['dev_count'])} (باز: {fa_num(s['dev_open'])})")
    lines.append(
        f"پیشنهادها: {fa_num(s['offers_count'])} | نرخ پذیرش: {fa_pct(s['offer_acceptance'])} | بهترین نوع: {s['best_offer_type']}")
    lines.append(
        f"پرداخت‌های عقب‌افتاده: {fa_money(s['overdue_amount'])} | چک برگشتی: {fa_num(s['bounced_checks'])}")
    lines.append(f"وضعیت کلی مشتری: {s['risk_level']}")
    lines.append("")
    lines.append("وضعیت ابعاد (به فارسی ساده):")
    lines.extend(_signal_lines(snapshot))
    lines.append("")
    lines.append("اقدام‌های پیشنهادی (فقط از این‌ها):")
    lines.extend(_action_lines(snapshot) or [" - هیچ"])
    return "\n".join(lines)


def _dashboard_prompt(snapshot: dict[str, Any]) -> str:
    s = snapshot
    lines: list[str] = []
    for k in s["kpis"]:
        lines.append(f"شاخص {k['label']}: {fa_num(k['value'])}")
    at = s["at_risk"]
    lines.append(
        f"مشتریان در معرض از دست رفتن: {fa_num(at.get('count', 0))} مشتری با درآمد {fa_money(at.get('revenue', 0))}")
    if s["complaint_themes"]:
        lines.append("موضوع‌های پرتکرار شکایت: " + "، ".join(
            f"{t['name']} ({fa_num(t['count'])} مورد)" for t in s["complaint_themes"][:4]))
    if s["offer_effectiveness"]:
        lines.append("پذیرش پیشنهادها بر اساس نوع: " + "؛ ".join(
            f"{o['type']}: {fa_pct(o['rate'])}" for o in s["offer_effectiveness"][:4]))
    col = s["collection_risk"]
    lines.append(
        f"مطالبات عقب‌افتاده: {fa_money(col.get('overdue', 0))} | چک برگشتی: {fa_num(col.get('bounced', 0))}")
    wb = s["winback"]
    lines.append(
        f"مشتریان قدیمی ارزشمند برای بازگرداندن: {fa_num(wb.get('count', 0))} مشتری با درآمد {fa_money(wb.get('revenue', 0))}")
    return "\n".join(lines)


def _next_action_prompt(snapshot: dict[str, Any]) -> str:
    """Plain-Persian context for the «اقدام بعدی» generator: the customer's key
    facts plus the signals and engine actions that MUST drive the choice."""
    s = snapshot
    lines = [
        f"مشتری: {s['customer_id']} | بخش بازار: {s['segment']} | وضعیت: {s['status']}",
        f"درآمد کل: {fa_money(s['revenue'])} | سفارش‌ها: {fa_num(s['orders'])} | آخرین خرید: {s['last_purchase']}",
        f"شکایت‌ها: {fa_num(s['complaints_count'])} (باز: {fa_num(s['unresolved_complaints'])})",
        f"پرداخت عقب‌افتاده: {fa_money(s['overdue_amount'])} | چک برگشتی: {fa_num(s['bounced_checks'])}",
        f"درخواست توسعه باز: {fa_num(s['dev_open'])} | پذیرش پیشنهاد: {fa_pct(s['offer_acceptance'])} | بهترین نوع: {s['best_offer_type']}",
        "",
        "سیگنال‌های محاسبه‌شده (منبع تصمیم):",
    ]
    lines.extend(_signal_lines(snapshot))
    lines.append("")
    lines.append("اقدام‌های پیشنهادی موتور (فقط از این‌ها انتخاب کن):")
    lines.extend(_action_lines(snapshot) or [" - فقط پایش"])
    return "\n".join(lines)


def _next_action_fallback(snapshot: dict[str, Any]) -> str:
    """Deterministic «اقدام بعدی» when no LLM is configured/callable: the
    engine's top-ranked action, formatted in the same four-line shape so the
    frontend renders it identically."""
    actions = snapshot.get("actions", [])
    if not actions:
        return (
            "اقدام اصلی: فقط پایش\n"
            "چرا الان: اقدام پیشنهادی مشخصی از موتور در دسترس نیست\n"
            "گام بعدی: وضعیت مشتری را در بازبینی بعدی پایش کنید\n"
            "اولویت: کم"
        )
    a = actions[0]
    name = a.get("name") or ACTION_FA.get(a.get("action_id", ""), a.get("action_id", ""))
    reason = a.get("reason", "") or "دلایل از سیگنال‌های مشتری در دسترس است"
    step = ACTION_NEXT_STEP_FA.get(
        a.get("action_id", ""), "با نماینده فروش هماهنگ کنید.")
    return (
        f"اقدام اصلی: {name}\n"
        f"چرا الان: {reason}\n"
        f"گام بعدی: {step}\n"
        "اولویت: بالا"
    )


# ---------------------------------------------------------------------------
# Cached generation with in-flight guard
# ---------------------------------------------------------------------------
_COMPUTING: set[str] = set()
_GUARD_LOCK = asyncio.Lock()


async def _generate(kind: str, key: str, context: dict[str, Any],
                    prompt_builder, fp: str, refresh: bool = False,
                    fallback: Callable[[dict[str, Any]], str] | None = None,
                    system: str = _SYSTEM,
                    value_key: str = "summary") -> dict[str, Any]:
    """Return ``{status, <value_key>: str | None, generated: bool}``.

    Without ``refresh`` this is a pure cache read: ready when the cached
    fingerprint matches, otherwise ``generating`` (a computation is in flight)
    or ``not_ready`` — it NEVER triggers generation.

    With ``refresh=True`` it regenerates on demand, even when the cached text
    is still fresh (that is the whole point of the «تازهسازی» button). If
    another computation for the same key is already in flight, it waits for
    that computation to finish and reuses its just-saved result instead of
    issuing a duplicate LLM call (no client polling loop either).

    ``fallback`` (callable(context) -> str) supplies the deterministic text used
    when no LLM is configured or the call fails; ``system`` is the system prompt
    for the LLM call; ``value_key`` names the result field (summary / nextAction)."""
    if not refresh:
        return await summary_status(kind, key, fp, value_key=value_key)

    while True:
        async with _GUARD_LOCK:
            if key in _COMPUTING:
                busy = True
            else:
                _COMPUTING.add(key)
                busy = False
        if not busy:
            break  # we own the computation slot — generate below
        # Someone else is already refreshing this key: wait for their result
        # to land, then reuse it (the save happens before the slot is freed).
        while True:
            async with _GUARD_LOCK:
                done = key not in _COMPUTING
            if done:
                break
            await asyncio.sleep(0.4)
        entry = store.load(kind, key)
        if entry is not None:
            return {"status": "ready", value_key: entry["value"], "generated": False}
        # (rare: the other computation crashed before saving — retry as owner)

    try:
        prompt = prompt_builder(context)
        fallback_text = fallback(context) if fallback else _fallback_summary(kind, prompt)
        summary = await _generate_llm(kind, prompt, fallback=fallback_text, system=system)
        store.save(kind, key, summary, fp)
        return {"status": "ready", value_key: summary, "generated": True}
    finally:
        async with _GUARD_LOCK:
            _COMPUTING.discard(key)


async def summary_status(kind: str, key: str, fp: str,
                         value_key: str = "summary") -> dict[str, Any]:
    """Pure cache-status read: ready / generating / not_ready. No generation."""
    entry = store.load(kind, key)
    if entry is not None and entry.get("fingerprint") == fp:
        return {"status": "ready", value_key: entry["value"], "generated": False}
    async with _GUARD_LOCK:
        in_flight = key in _COMPUTING
    if in_flight:
        return {"status": "generating", value_key: None, "generated": False}
    return {"status": "not_ready", value_key: None, "generated": False}


async def _generate_llm(kind: str, user_prompt: str,
                        fallback: str | None = None,
                        system: str = _SYSTEM) -> str:
    if not settings.has_key:
        return fallback if fallback is not None else _fallback_summary(kind, user_prompt)
    try:
        raw = await _llm_call_async(system, user_prompt, temperature=0.3)
        text = (raw or "").strip()
        if text:
            return text
    except Exception:  # noqa: BLE001 — degrade gracefully to the fallback
        pass
    return fallback if fallback is not None else _fallback_summary(kind, user_prompt)


def _fallback_summary(kind: str, user_prompt: str) -> str:
    """Deterministic plain-language summary when no LLM is configured/callable."""
    return (
        "وضعیت کلی: این خلاصه از روی داده‌های موجود در سامانه ساخته شده است.\n\n"
        "نکات مهم:\n" + user_prompt + "\n\n"
        "پیشنهاد اقدام: پیشنهادهای بالا را با نماینده فروش هماهنگ کنید."
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
async def customer_summary(payload: dict[str, Any],
                           refresh: bool = False) -> dict[str, Any]:
    """LLM summary for one customer (cached by fingerprint of its /360 payload)."""
    snapshot = _customer_snapshot(payload)
    fp = store.fingerprint(snapshot)
    key = str(payload.get("customer", {}).get("Customer_ID") or "unknown")
    return await _generate("customer360", key, snapshot, _customer_prompt,
                           fp, refresh=refresh)


async def customer_next_action(payload: dict[str, Any],
                               refresh: bool = False) -> dict[str, Any]:
    """LLM-generated «اقدام بعدی» for one customer (cached).

    The generator consumes the engine's computed signals/state/actions (the
    product's tools) — never invents an action or number. Cached per customer
    under the SAME snapshot fingerprint as the summary, so both invalidate
    together and plain reads are cheap cache lookups (ready / generating /
    not_ready — never triggers generation). Without an LLM the deterministic
    top engine action is used, in the same four-line shape."""
    snapshot = _customer_snapshot(payload)
    fp = store.fingerprint(snapshot)
    key = str(payload.get("customer", {}).get("Customer_ID") or "unknown")
    return await _generate("customer_next_action", key, snapshot,
                           _next_action_prompt, fp, refresh=refresh,
                           fallback=_next_action_fallback,
                           system=_NEXT_ACTION_SYSTEM,
                           value_key="nextAction")


async def dashboard_summary(det: dict[str, Any],
                            refresh: bool = False,
                            fp: str | None = None) -> dict[str, Any]:
    """LLM portfolio summary for the dashboard.

    ``fp`` lets the caller use a cheap portfolio fingerprint (counts + newest
    dates) as the cache key, so plain reads never need to rebuild the full
    dashboard payload. When omitted, the snapshot fingerprint is used."""
    snapshot = _dashboard_snapshot(det)
    if fp is None:
        fp = store.fingerprint(snapshot)
    return await _generate("dashboard", "overview", snapshot,
                           _dashboard_prompt, fp, refresh=refresh)
