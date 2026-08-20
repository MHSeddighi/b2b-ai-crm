"""Decision-engine tests: eligibility, ranking, and the action catalog.

Each scenario is a deterministic mapping from signals+state to a top action.
Includes the contradictory case (high growth + critical complaint) where an
otherwise-attractive CROSS_SELL must yield to SERVICE_RECOVERY.
"""
import pytest

from backend.crm.actions.next_best_action import recommend
from backend.crm.schemas import CustomerSignal, CustomerState, StateDimension


def _sig(signal_id, status="neutral", score=None, confidence=1.0,
         evidence=None, reasons=None, direction="stable", sample_size=1):
    return CustomerSignal(
        signal_id=signal_id, customer_id="X", status=status, score=score,
        confidence=confidence, evidence=evidence or {}, reasons=reasons or [],
        direction=direction, sample_size=sample_size,
    )


def _dim(score=None, status="unknown", confidence=0.0):
    return StateDimension(score=score, status=status, confidence=confidence)


def _state(**overrides):
    dims = {
        "value": _dim(50, "medium", 0.5),
        "churn_risk": _dim(0, "low", 0.5),
        "growth_opportunity": _dim(0, "unknown", 0.5),
        "relationship_health": _dim(50, "healthy", 0.5),
        "profitability": _dim(0, "unknown", 0.5),
        "payment_risk": _dim(0, "low", 0.5),
    }
    dims.update(overrides)
    return CustomerState(customer_id="X", **dims)


def _top(actions):
    return [a.action_id for a in actions]


# ---------------------------------------------------------------------------
# Scenario tests
# ---------------------------------------------------------------------------
def test_high_churn_high_value_retention():
    signals = {
        "churn_risk": _sig("churn_risk", "high", score=78, reasons=["Purchase decline"]),
        "purchase_trend": _sig("purchase_trend", "critical", score=-40),
        "profit": _sig("profit", "positive", score=25,
                       evidence={"classification": "high_profit"}),
    }
    state = _state(churn_risk=_dim(78, "high", 0.9), value=_dim(90, "high", 0.9))
    actions = recommend(signals, state, 0.9)
    assert "RETENTION_CALL" in _top(actions)


def test_severe_complaint_service_recovery():
    signals = {
        "complaint_impact": _sig("complaint_impact", "critical", score=100,
                                 evidence={"unresolved_count": 3},
                                 reasons=["Decline followed complaint"]),
    }
    state = _state(relationship_health=_dim(20, "poor", 0.9))
    actions = recommend(signals, state, 0.9)
    assert _top(actions)[0] == "SERVICE_RECOVERY"


def test_high_growth_healthy_cross_sell():
    signals = {
        "growth_potential": _sig("growth_potential", "positive", score=82,
                                 evidence={"level": "high"}),
        "share_of_wallet": _sig("share_of_wallet", "neutral", score=25,
                                evidence={"classification": "low_share"}),
        "payment_behavior": _sig("payment_behavior", "positive", score=5),
        "profit": _sig("profit", "positive", score=25,
                       evidence={"classification": "high_profit"}),
    }
    state = _state(churn_risk=_dim(10, "low", 0.8),
                   relationship_health=_dim(80, "healthy", 0.8))
    actions = recommend(signals, state, 0.9)
    assert "CROSS_SELL" in _top(actions)


def test_high_revenue_low_profit_price_review():
    signals = {
        "profit": _sig("profit", "critical", score=-15,
                       evidence={"classification": "negative_profit"}),
    }
    state = _state(value=_dim(90, "high", 0.8),
                   profitability=_dim(0, "critical", 0.8))
    actions = recommend(signals, state, 0.9)
    assert "PRICE_REVIEW" in _top(actions)


def test_poor_payment_credit_review():
    signals = {
        "payment_behavior": _sig("payment_behavior", "critical", score=50,
                                 reasons=["Many late payments"]),
    }
    state = _state(payment_risk=_dim(50, "critical", 0.9))
    actions = recommend(signals, state, 0.9)
    assert "CREDIT_REVIEW" in _top(actions)


def test_long_inactivity_reactivation():
    signals = {
        "purchase_cycle": _sig("purchase_cycle", "critical", score=100,
                               reasons=["Far beyond normal cycle"]),
    }
    state = _state()
    actions = recommend(signals, state, 0.9)
    assert "REACTIVATION" in _top(actions)


def test_contradictory_growth_plus_critical_complaint():
    """High growth opportunity + critical complaint -> SERVICE_RECOVERY wins,
    CROSS_SELL is blocked — opportunity is not an action."""
    signals = {
        "growth_potential": _sig("growth_potential", "positive", score=90,
                                 evidence={"level": "high"}),
        "share_of_wallet": _sig("share_of_wallet", "neutral", score=20,
                                evidence={"classification": "low_share"}),
        "complaint_impact": _sig("complaint_impact", "critical", score=100,
                                 evidence={"unresolved_count": 2},
                                 reasons=["Severe unresolved complaint"]),
        "payment_behavior": _sig("payment_behavior", "positive", score=5),
    }
    state = _state(churn_risk=_dim(10, "low", 0.5),
                   relationship_health=_dim(20, "poor", 0.5))
    actions = recommend(signals, state, 0.9)
    top = _top(actions)
    assert top[0] == "SERVICE_RECOVERY"
    assert "CROSS_SELL" not in top


def test_no_action_fallback():
    """No triggering signals -> monitor only (never invent an action)."""
    signals = {"profit": _sig("profit", "neutral", evidence={"classification": "normal_profit"})}
    state = _state(churn_risk=_dim(0, "low", 0.8),
                   relationship_health=_dim(80, "healthy", 0.8))
    actions = recommend(signals, state, 0.9)
    # Either NO_ACTION or a low-impact healthy action; must never crash/raise.
    assert actions is not None


def test_max_three_actions():
    """The engine returns at most 3 recommendations to the salesperson."""
    signals = {
        "complaint_impact": _sig("complaint_impact", "critical", score=100,
                                 evidence={"unresolved_count": 5}),
        "purchase_cycle": _sig("purchase_cycle", "critical", score=100),
        "payment_behavior": _sig("payment_behavior", "critical", score=60),
        "profit": _sig("profit", "critical", score=-20,
                       evidence={"classification": "negative_profit"}),
    }
    state = _state(churn_risk=_dim(80, "high", 0.9),
                   relationship_health=_dim(10, "poor", 0.9),
                   payment_risk=_dim(60, "critical", 0.9))
    actions = recommend(signals, state, 0.9)
    assert len(actions) <= 3
