"""Centralized, configurable thresholds for the Customer Intelligence engine.

Nothing business-critical is hard-coded inside signal/action code — the
business team can tune these values here without touching the calculation
logic. Every threshold is documented so a non-engineer can change it safely.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Enumerated vocabularies (shared across signals/state/actions)
# ---------------------------------------------------------------------------
SIGNAL_STATUSES = ("positive", "neutral", "warning", "critical", "unknown")
SIGNAL_DIRECTIONS = ("improving", "stable", "declining", "neutral", "unknown")

# --- Confusable statuses, intentionally kept distinct ---
# "unknown"       -> not enough data to say anything (confidence ~0)
# "low_confidence" -> a value exists but sample is too small to trust

# ---------------------------------------------------------------------------
# Time windows / reference date
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class TimeConfig:
    # Rolling window (days) used for "recent vs previous comparable period".
    recent_window_days: int = 90
    previous_window_days: int = 90
    # Minimum orders for a customer to trust cycle/trend statistics.
    min_orders_for_cycle: int = 3
    min_orders_for_trend: int = 3
    # Payment trend: recent window vs the window before it (days).
    payment_recent_days: int = 180
    payment_baseline_days: int = 180
    # Complaint impact: purchase window around a complaint (days).
    complaint_before_days: int = 90
    complaint_after_days: int = 90
    # Share-of-wallet: number of trailing months to average.
    wallet_months: int = 3
    # Margin trend: months per comparison period.
    margin_period_months: int = 3


TIME = TimeConfig()


# ---------------------------------------------------------------------------
# Signal 1 — Real Profit
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ProfitConfig:
    # Profit margin classification thresholds (fraction, not percent).
    high_profit_margin: float = 0.25
    normal_profit_margin: float = 0.10
    low_profit_margin: float = 0.00
    # Below this margin the customer is "negative_profit".
    # Minimum cost coverage (costed revenue / total revenue) to trust a margin.
    min_cost_coverage: float = 0.5


# ---------------------------------------------------------------------------
# Signal 2 — Purchase Trend
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class PurchaseTrendConfig:
    strong_growth: float = 0.30
    growth: float = 0.10
    decline: float = -0.10
    strong_decline: float = -0.30
    # Treat |change| below this as "stable" (avoid noise on tiny bases).
    stable_band: float = 0.10


# ---------------------------------------------------------------------------
# Signal 3 — Payment Behaviour
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class PaymentConfig:
    excellent_delay: float = 7.0
    good_delay: float = 15.0
    warning_delay: float = 30.0
    poor_delay: float = 45.0
    # Deterioration: recent avg delay vs historical avg delay (days).
    deterioration_days: float = 10.0
    # Late invoice threshold (days).
    late_threshold_days: float = 15.0
    # Overdue ratio (late invoices / total) thresholds.
    overdue_ratio_warning: float = 0.25
    overdue_ratio_critical: float = 0.5


# ---------------------------------------------------------------------------
# Signal 4 — Share of Wallet
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ShareOfWalletConfig:
    low_share: float = 0.35
    high_share: float = 0.65
    # Min sample of months required to report a share.
    min_months: int = 1
    # If the newest wallet row is older than this (days) -> mark stale/low conf.
    stale_days: int = 365


# ---------------------------------------------------------------------------
# Signal 5 — Purchase Cycle Deviation
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class PurchaseCycleConfig:
    warning_ratio: float = 1.25
    critical_ratio: float = 1.75


# ---------------------------------------------------------------------------
# Signal 6 — Margin Trend
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class MarginTrendConfig:
    improving: float = 0.03
    declining: float = -0.03
    strong_decline: float = -0.10
    stable_band: float = 0.03


# ---------------------------------------------------------------------------
# Signal 9 — Complaint Impact
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ComplaintImpactConfig:
    decline_warning: float = -0.20
    decline_critical: float = -0.40
    recovery_days: int = 45  # "no recovery after N days" -> still hurting
    # Severity weights (critical > high > medium > low).
    severity_weight: dict = field(default_factory=lambda: {
        "بحرانی": 3.0, "زیاد": 2.0, "متوسط": 1.0, "کم": 0.5,
    })


# ---------------------------------------------------------------------------
# Signal 10 — Offer Affinity
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class OfferAffinityConfig:
    min_sample: int = 3          # min accepted+rejected per type to infer
    min_response_rate: float = 0.5  # above this -> "positive" affinity


# ---------------------------------------------------------------------------
# Derived signals — churn risk / growth potential
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class DerivedConfig:
    # Churn risk: number of strong negative *evidence groups* required per band.
    churn_warning_groups: int = 2
    churn_high_groups: int = 3
    churn_critical_groups: int = 4
    # Confidence floor below which we refuse to call a churn risk.
    churn_min_confidence: float = 0.3


# ---------------------------------------------------------------------------
# Aggregated configuration object
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class SignalConfig:
    time: TimeConfig = field(default_factory=TimeConfig)
    profit: ProfitConfig = field(default_factory=ProfitConfig)
    purchase_trend: PurchaseTrendConfig = field(default_factory=PurchaseTrendConfig)
    payment: PaymentConfig = field(default_factory=PaymentConfig)
    share_of_wallet: ShareOfWalletConfig = field(default_factory=ShareOfWalletConfig)
    purchase_cycle: PurchaseCycleConfig = field(default_factory=PurchaseCycleConfig)
    margin_trend: MarginTrendConfig = field(default_factory=MarginTrendConfig)
    complaint_impact: ComplaintImpactConfig = field(default_factory=ComplaintImpactConfig)
    offer_affinity: OfferAffinityConfig = field(default_factory=OfferAffinityConfig)
    derived: DerivedConfig = field(default_factory=DerivedConfig)


SIGNAL_CONFIG = SignalConfig()
