"""Signal 10 — Offer Affinity.

Response rate (accepted vs rejected) per offer mechanism, from the ``offers``
table. Never infers a preference from fewer than ``min_sample`` responses.
"""
from __future__ import annotations

import datetime as dt

import duckdb

from backend.crm.config import OfferAffinityConfig, SignalConfig
from backend.crm.schemas import CustomerSignal
from backend.crm.signals.base import signal


_OFFER_SQL = """
SELECT "Offer_Type",
       SUM(CASE WHEN "Result" = 'قبول' THEN 1 ELSE 0 END) AS accepted,
       SUM(CASE WHEN "Result" = 'رد' THEN 1 ELSE 0 END) AS rejected
FROM offers
WHERE Customer_ID = ?
GROUP BY "Offer_Type"
"""

_TYPE_CATEGORY = {
    "حجمی": "volume_offer",
    "قیمتی": "discount",
    "مدت\u200cدار": "payment_terms",
}


def calculate(con: duckdb.DuckDBPyConnection, customer_id: str,
              ref: dt.date, cfg: SignalConfig) -> CustomerSignal:
    rows = con.execute(_OFFER_SQL, [customer_id]).fetchall()

    by_type: dict[str, dict] = {}
    total_accepted = total_rejected = 0
    for offer_type, accepted, rejected in rows:
        a, r = int(accepted or 0), int(rejected or 0)
        cat = _TYPE_CATEGORY.get(offer_type, "other")
        by_type[cat] = {
            "accepted": a, "rejected": r,
            "total": a + r,
            "rate": (a / (a + r)) if (a + r) else None,
        }
        total_accepted += a
        total_rejected += r

    decided = total_accepted + total_rejected

    # Prefer the mechanism with the best response rate among types that have
    # enough decided responses to be trustworthy.
    preferred = None
    best_rate = -1.0
    for cat, d in by_type.items():
        if d["total"] >= cfg.offer_affinity.min_sample and d["rate"] is not None:
            if d["rate"] > best_rate:
                best_rate = d["rate"]
                preferred = cat

    if decided == 0:
        return signal("offer_affinity", customer_id, status="unknown",
                      confidence=0.0, sample_size=0,
                      reasons=["No offer response history available"])

    if preferred is None:
        return signal("offer_affinity", customer_id, status="unknown",
                      confidence=0.0, sample_size=decided,
                      evidence={"accepted": total_accepted,
                                "rejected": total_rejected,
                                "by_type": by_type},
                      reasons=["Insufficient offer history to infer preference"])

    confidence = min(1.0, by_type[preferred]["total"] / (cfg.offer_affinity.min_sample * 3))

    return signal(
        "offer_affinity", customer_id,
        value=best_rate,
        score=round(best_rate * 100, 2),
        status="positive" if best_rate >= cfg.offer_affinity.min_response_rate else "neutral",
        direction="stable",
        confidence=round(confidence, 3),
        sample_size=decided,
        evidence={
            "preferred_offer_type": preferred,
            "accepted": by_type[preferred]["accepted"],
            "rejected": by_type[preferred]["rejected"],
            "response_rate": round(best_rate, 3),
            "by_type": {
                k: {"accepted": v["accepted"], "rejected": v["rejected"],
                    "response_rate": round(v["rate"], 3) if v["rate"] is not None else None}
                for k, v in by_type.items()
            },
        },
        reasons=[f"Customer responds best to {preferred} offers "
                 f"({by_type[preferred]['accepted']} accepted / "
                 f"{by_type[preferred]['rejected']} rejected)"],
    )
