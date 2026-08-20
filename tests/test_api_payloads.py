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
        first = await intel_summary.customer_summary(payload)
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
        first = await intel_summary.dashboard_summary(det)
        assert first["status"] == "ready"
        second = await intel_summary.dashboard_summary(det)
        assert second["generated"] is False
        assert second["summary"] == first["summary"]
    asyncio.run(run())
