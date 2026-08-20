"""Tests for the real-data API payloads (dashboard intelligence, analyses,
customer 360 sections, cached LLM summaries)."""
from __future__ import annotations

import asyncio

import pytest

from backend import api_data
from backend.agents import intel_summary
from backend.crm import cache as store


def _any_customer() -> str:
    return api_data.customers()[0]["Customer_ID"]


def test_customer_360_has_all_sections():
    payload = api_data.customer_360(_any_customer())
    assert payload is not None
    for key in (
        "customer", "summary", "summaryReady", "riskLevel", "riskSignals",
        "actions", "orders", "revenue", "complaints", "complaintList",
        "interactions", "interactionsCount", "transactions", "devRequests",
        "devCount", "devOpen", "offers", "offerAcceptance", "collections",
        "collectionsCount", "overdueAmount", "bouncedChecks", "marketSignals",
    ):
        assert key in payload, f"missing {key}"
    assert isinstance(payload["complaintList"], list)
    assert isinstance(payload["interactions"], list)
    assert isinstance(payload["transactions"], list)
    assert isinstance(payload["devRequests"], list)
    assert isinstance(payload["offers"], list)
    assert isinstance(payload["collections"], list)


def test_customer_360_unknown_customer_returns_none():
    assert api_data.customer_360("C_DOES_NOT_EXIST_999") is None


def test_customer_360_signal_and_action_shapes():
    payload = api_data.customer_360(_any_customer())
    for sig in payload["riskSignals"]:
        assert sig["label"]
        assert sig["tone"] in ("positive", "negative", "neutral")
    for act in payload["actions"]:
        assert act["id"] and act["name"] and act["reason"]


def test_dashboard_includes_intelligence_and_recommendations():
    data = api_data.dashboard()
    intel = data["intelligence"]
    assert {"at_risk", "complaint_themes", "offer_effectiveness",
            "collection_risk", "winback", "segment_share"} <= set(intel)
    assert intel["at_risk"]["count"] >= 0
    assert isinstance(data["recommendations"], list)
    for rec in data["recommendations"]:
        assert rec["title"] and rec["detail"] and rec["tone"] in (
            "positive", "warning", "negative")


def test_analyses_payload_shapes():
    data = api_data.analyses()
    assert {"atRisk", "complaintThemes", "revenueConcentration",
            "churnFactors", "incomeRecommendations"} <= set(data)
    assert isinstance(data["atRisk"], list) and data["atRisk"]
    assert isinstance(data["incomeRecommendations"], list)
    cf = data["churnFactors"]
    assert {"never_bought", "inactive_180_365", "inactive_over_365",
            "inactive_with_complaints"} <= set(cf)


def test_customer_summary_cached_and_reused(monkeypatch):
    async def fake_generate_llm(kind, prompt):
        return ("وضعیت کلی: مشتری در وضعیت نیازمند توجه است.\n\n"
                "نکات مهم:\n - شکایت باز وجود دارد.\n\n"
                "پیشنهاد اقدام:\n - رسیدگی به شکایت‌ها.")
    monkeypatch.setattr(intel_summary, "_generate_llm", fake_generate_llm)

    cid = _any_customer()
    # start from a clean cache so "generated" flags are deterministic
    for kind, key in (("customer360", cid), ("customer360_data", cid)):
        p = store._path(kind, key)
        if p.exists():
            p.unlink()

    async def run():
        payload = api_data.customer_360(cid)
        # Without cache and without refresh -> not_ready (never auto-generates)
        not_ready = await intel_summary.customer_summary(payload)
        assert not_ready["status"] == "not_ready"
        # Explicit refresh triggers generation once, then it is cached
        first = await intel_summary.customer_summary(payload, refresh=True)
        assert first["status"] == "ready"
        assert first["generated"] is True
        second = await intel_summary.customer_summary(payload)
        assert second["status"] == "ready"
        assert second["generated"] is False
        assert second["summary"] == first["summary"]
    asyncio.run(run())


def test_dashboard_summary_cached_and_reused(monkeypatch):
    async def fake_generate_llm(kind, prompt):
        return ("وضعیت کلی: فروش روند رو به رشدی دارد.\n\n"
                "پیشنهاد اقدام:\n - تمرکز روی مشتریان پرریسک.")
    monkeypatch.setattr(intel_summary, "_generate_llm", fake_generate_llm)

    p = store._path("dashboard", "overview")
    if p.exists():
        p.unlink()

    async def run():
        det = api_data.dashboard()
        not_ready = await intel_summary.dashboard_summary(det)
        assert not_ready["status"] == "not_ready"
        first = await intel_summary.dashboard_summary(det, refresh=True)
        assert first["status"] == "ready"
        # A FRESH payload must produce the same cache key (ties in ORDER BY are
        # broken deterministically, so the fingerprint never drifts).
        det2 = api_data.dashboard()
        second = await intel_summary.dashboard_summary(det2)
        assert second["status"] == "ready"
        assert second["generated"] is False
        assert second["summary"] == first["summary"]
    asyncio.run(run())


def test_customer_summary_fingerprint_stable_across_fresh_payloads(monkeypatch):
    async def fake_generate_llm(kind, prompt):
        return "وضعیت کلی: مشتری نیازمند توجه است."
    monkeypatch.setattr(intel_summary, "_generate_llm", fake_generate_llm)

    cid = _any_customer()
    for kind, key in (("customer360", cid), ("customer360_data", cid)):
        p = store._path(kind, key)
        if p.exists():
            p.unlink()

    async def run():
        p1 = api_data.customer_360(cid)
        first = await intel_summary.customer_summary(p1, refresh=True)
        assert first["status"] == "ready"
        p2 = api_data.customer_360(cid)  # fresh payload, same data
        second = await intel_summary.customer_summary(p2)
        assert second["status"] == "ready"
        assert second["generated"] is False
        assert second["summary"] == first["summary"]
    asyncio.run(run())


def test_engine_at_risk_is_cached_and_ranked():
    from backend.crm.at_risk import engine_at_risk
    rows1 = engine_at_risk(10)
    rows2 = engine_at_risk(10)
    assert rows1 == rows2, "engine at-risk must be cached and deterministic"
    assert rows1, "expected at least one ranked customer"
    scores = [r["risk_score"] for r in rows1]
    assert scores == sorted(scores, reverse=True), "must be sorted by risk desc"
    for r in rows1:
        assert r["risk_level"] in ("زیاد", "متوسط", "کم")
        assert r["customer_id"]


# ---------------------------------------------------------------------------
# Persian labels
# ---------------------------------------------------------------------------
def test_reason_translator_covers_engine_templates():
    from backend.crm.labels import translate_reason
    import re
    cases = [
        "2 bounced cheque(s)",
        "172/259 payments are late",
        "11 unresolved complaint(s) remain",
        "54 open development request(s)",
        "Customer is 1507 days since last purchase vs a normal cycle of 7 days (ratio 215.29)",
        "Customer responds best to discount offers (18 accepted / 17 rejected)",
        "Customer responds best to payment_terms offers (3 accepted / 1 rejected)",
        "Share of wallet is 35% (3 month(s), source: فروش کارشناس، مشتری اظهار)",
        "Profit margin is 73.0% but cost data covers only 29% of revenue, so it is not reliable",
        "Purchase decline (-100%) followed the complaint",
        "Revenue changed +12.5% (40 vs 35 orders)",
        "Total revenue 153,046,766",
        "Payment behaviour deteriorating",
        "Customer is far beyond normal purchase cycle",
        "No complaints on record",
        "Insufficient history: no comparable previous period",
        "Margin moved from 25.0% to 30.0% (change +5.0%)",
    ]
    for eng in cases:
        fa = translate_reason(eng)
        assert re.search(r"[a-zA-Z]", fa) is None, f"left English: {eng!r} -> {fa!r}"
        assert fa != eng


def test_360_payload_translated_fields_are_persian():
    import re
    payload = api_data.customer_360(_any_customer())
    for sig in payload["riskSignals"]:
        assert re.search(r"[a-zA-Z]", sig["label"]) is None
        for reason in sig["reasons"]:
            assert re.search(r"[a-zA-Z]", reason) is None, reason
    for act in payload["actions"]:
        assert re.search(r"[a-zA-Z]", act["name"]) is None, act["name"]
        assert re.search(r"[a-zA-Z]", act["reason"]) is None, act["reason"]
        assert re.search(r"[a-zA-Z]", act["next_step"]) is None, act["next_step"]
    for dim, v in payload["state"].items():
        assert re.search(r"[a-zA-Z]", v["status"]) is None, v["status"]
        for reason in v["reasons"]:
            assert re.search(r"[a-zA-Z]", reason) is None, reason


def test_customer_360_profile_is_curated_persian():
    payload = api_data.customer_360(_any_customer())
    prof = payload["customerProfile"]
    assert prof, "profile should not be empty"
    for f in prof:
        assert f["label"]
        # raw internal ids/system fields must not leak into the profile
        assert not any(x in f["label"] for x in ("ID", "Source", "Location")), f["label"]


def test_analyses_cached():
    first = api_data.analyses()
    second = api_data.analyses()
    assert first == second
