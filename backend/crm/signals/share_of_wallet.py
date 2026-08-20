"""Signal 4 — Share of Wallet.

our_purchase / estimated_total_customer_purchase. Only computed from the
``wallet_share`` external estimate — never reconstructed from our own sales
(that would be circular). Returns ``unknown`` when no external estimate exists.
"""
from __future__ import annotations

import datetime as dt

import duckdb

from backend.crm.config import ShareOfWalletConfig, SignalConfig
from backend.crm.data import as_date, safefloat
from backend.crm.schemas import CustomerSignal
from backend.crm.signals.base import signal


_SOW_SQL = """
SELECT "Month_Key", "Estimated_Total_Purchase", "Nafis_Purchase",
       "Estimate_Source", "Main_Competitor"
FROM wallet_share
WHERE Customer_ID = ?
ORDER BY "Month_Key" DESC
LIMIT ?
"""


def _classify(share: float, cfg: ShareOfWalletConfig) -> str:
    if share >= cfg.high_share:
        return "high_share"
    if share <= cfg.low_share:
        return "low_share"
    return "medium_share"


_STATUS = {"high_share": "positive", "medium_share": "neutral",
           "low_share": "neutral"}


def calculate(con: duckdb.DuckDBPyConnection, customer_id: str,
              ref: dt.date, cfg: SignalConfig) -> CustomerSignal:
    rows = con.execute(_SOW_SQL, [customer_id, cfg.time.wallet_months]).fetchall()

    if not rows:
        return signal("share_of_wallet", customer_id, status="unknown",
                      confidence=0.0, sample_size=0,
                      reasons=["No external wallet-share estimate available"])

    our_spend = sum(safefloat(r[2]) or 0.0 for r in rows)
    est_total = sum(safefloat(r[1]) or 0.0 for r in rows)
    sources = {r[3] for r in rows if r[3]}

    if est_total <= 0:
        return signal("share_of_wallet", customer_id, status="unknown",
                      confidence=0.0, sample_size=len(rows),
                      reasons=["External total-spend estimate is zero/missing"])

    share = our_spend / est_total
    classification = _classify(share, cfg.share_of_wallet)

    # Staleness: newest month vs reference date.
    latest_month = rows[0][0]
    stale_days = None
    try:
        # Month_Key is 'YYYY-MM'; approximate its end as the last day of month.
        y, m = (int(x) for x in str(latest_month).split("-"))
        month_end = (dt.date(y, m, 1) + dt.timedelta(days=32)).replace(day=1) \
            - dt.timedelta(days=1)
        stale_days = (ref - month_end).days
    except (ValueError, TypeError):
        stale_days = None

    confidence = min(1.0, len(rows) / cfg.time.wallet_months)
    if stale_days is not None and stale_days > cfg.share_of_wallet.stale_days:
        confidence = min(confidence, 0.4)

    reasons = [f"Share of wallet is {share:.0%} ({len(rows)} month(s), "
               f"source: {', '.join(sorted(sources)) or 'unknown'})"]
    if stale_days is not None and stale_days > cfg.share_of_wallet.stale_days:
        reasons.append(f"Wallet estimate is {stale_days} days old")

    return signal(
        "share_of_wallet", customer_id,
        value=round(share, 4),
        score=round(share * 100, 2),
        status=_STATUS[classification],
        direction="neutral",
        confidence=round(confidence, 3),
        sample_size=len(rows),
        evidence={
            "classification": classification,
            "our_spend": round(our_spend, 2),
            "estimated_total_spend": round(est_total, 2),
            "share_pct": round(share * 100, 2),
            "data_source": sorted(sources),
            "months": len(rows),
            "latest_month": latest_month,
            "stale_days": stale_days,
            "main_competitor": rows[0][4],
        },
        reasons=reasons,
    )
