"""Structured contracts for the Customer Intelligence layer.

These pydantic models are the canonical shape of every signal, state
dimension, reason, and action. The chatbot tools serialize these directly,
so the LLM always consumes structured, backend-owned values.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Signal
# ---------------------------------------------------------------------------
class CustomerSignal(BaseModel):
    signal_id: str
    customer_id: str
    score: float | None = None          # 0..100 normalized where meaningful
    value: float | None = None          # raw underlying value (e.g. change pct)
    status: str = "unknown"             # positive|neutral|warning|critical|unknown
    direction: str = "unknown"          # improving|stable|declining|neutral|unknown
    confidence: float = 0.0             # 0..1
    sample_size: int = 0
    evidence: dict[str, Any] = Field(default_factory=dict)
    reasons: list[str] = Field(default_factory=list)
    calculated_at: datetime = Field(default_factory=_now)


# ---------------------------------------------------------------------------
# Reason / evidence
# ---------------------------------------------------------------------------
class Reason(BaseModel):
    reason_id: str
    type: str                            # e.g. PURCHASE_DECLINING
    severity: str = "neutral"            # positive|neutral|warning|critical
    confidence: float = 0.0
    evidence: dict[str, Any] = Field(default_factory=dict)
    source_signals: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Customer state dimensions
# ---------------------------------------------------------------------------
class StateDimension(BaseModel):
    score: float | None = None
    status: str = "unknown"
    confidence: float = 0.0
    reasons: list[str] = Field(default_factory=list)
    evidence: dict[str, Any] = Field(default_factory=dict)


class CustomerState(BaseModel):
    customer_id: str
    value: StateDimension = Field(default_factory=StateDimension)
    churn_risk: StateDimension = Field(default_factory=StateDimension)
    growth_opportunity: StateDimension = Field(default_factory=StateDimension)
    relationship_health: StateDimension = Field(default_factory=StateDimension)
    profitability: StateDimension = Field(default_factory=StateDimension)
    payment_risk: StateDimension = Field(default_factory=StateDimension)


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------
class ActionDefinition(BaseModel):
    action_id: str
    name: str
    description: str
    category: str
    # Declarative, config-driven eligibility/priority inputs (see actions/).
    business_impact: float = 0.5
    urgency_weight: float = 0.5
    # Rule is evaluated by actions.eligibility; keys reference signal/state data.
    eligibility: dict[str, Any] = Field(default_factory=dict)
    forbidden: dict[str, Any] = Field(default_factory=dict)


class RecommendedAction(BaseModel):
    action_id: str
    name: str
    category: str = ""                  # relationship | quality | sales | commercial | collection | attention
    priority: float                     # 0..1
    confidence: float                   # 0..1
    reason: str
    evidence: list[str] = Field(default_factory=list)
    suggested_next_step: str = ""
    blocked_actions: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Data quality
# ---------------------------------------------------------------------------
class DataQuality(BaseModel):
    overall: float = 0.0
    warnings: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Canonical customer-intelligence object
# ---------------------------------------------------------------------------
class CustomerIntelligence(BaseModel):
    customer_id: str
    signals: dict[str, CustomerSignal] = Field(default_factory=dict)
    state: CustomerState | None = None
    reasons: list[Reason] = Field(default_factory=list)
    next_best_actions: list[RecommendedAction] = Field(default_factory=list)
    data_quality: DataQuality = Field(default_factory=DataQuality)
    calculated_at: datetime = Field(default_factory=_now)
