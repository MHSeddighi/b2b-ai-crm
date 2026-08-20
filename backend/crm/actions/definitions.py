"""Action catalog — declarative, config-driven definitions.

Eligibility/forbidden conditions are data structures (evaluated by
``eligibility.py``), not scattered if/else blocks. Business impact and the
signals that drive urgency/confidence are declared here so the business team
can tune them without touching ranking logic.
"""
from __future__ import annotations

from backend.crm.schemas import ActionDefinition

# Condition vocabulary (see eligibility.evaluate):
#   {"signal": id, "status": [..]}           signal.status in [..]
#   {"signal": id, "score_ge": n}            signal.score >= n
#   {"signal": id, "score_le": n}            signal.score <= n
#   {"signal": id, "evidence_ge": {k: n}}    signal.evidence[k] >= n
#   {"state": dim, "status": [..]}           state.dim.status in [..]
#   {"state": dim, "score_ge": n}            state.dim.score >= n


# urgency/confidence sources + suggested next step are kept in a parallel
# registry keyed by action_id (the ActionDefinition schema stays clean).
_ACTION_META: dict[str, dict] = {}


def _def(action_id: str, name: str, description: str, category: str,
         business_impact: float, eligibility: dict, forbidden: dict,
         urgency_signals: list[str], confidence_signals: list[str],
         next_step: str) -> ActionDefinition:
    _ACTION_META[action_id] = {
        "business_impact": business_impact,
        "urgency_signals": urgency_signals,
        "confidence_signals": confidence_signals,
        "next_step": next_step,
    }
    return ActionDefinition(
        action_id=action_id, name=name, description=description,
        category=category, business_impact=business_impact,
        eligibility=eligibility, forbidden=forbidden,
    )


ACTIONS: list[ActionDefinition] = [
    _def(
        "RETENTION_CALL", "Retention call", "Proactively contact an at-risk, high-value customer.", "relationship",
        0.9,
        {"all": [
            {"state": "churn_risk", "status": ["high", "critical"]},
            {"state": "value", "status": ["high", "medium"]},
        ]},
        {},
        ["churn_risk"], ["churn_risk", "purchase_trend"],
        "Account manager should call the customer to understand the decline and re-engage before it worsens.",
    ),
    _def(
        "SERVICE_RECOVERY", "Service recovery", "Resolve an unresolved complaint affecting the relationship.", "quality",
        1.0,
        {"any": [
            {"signal": "complaint_impact", "status": ["critical", "warning"]},
            {"signal": "complaint_impact", "evidence_ge": {"unresolved_count": 1}},
        ]},
        {},
        ["complaint_impact"], ["complaint_impact"],
        "Resolve the complaint and confirm satisfaction before proposing any additional sales.",
    ),
    _def(
        "ACCOUNT_REVIEW", "Account review", "Review a deteriorating relationship end-to-end.", "relationship",
        0.6,
        {"any": [
            {"state": "relationship_health", "status": ["poor", "warning"]},
        ]},
        {},
        ["churn_risk"], ["churn_risk", "complaint_impact", "payment_behavior"],
        "Schedule an account review to reassess the relationship and future plan.",
    ),
    _def(
        "CROSS_SELL", "Cross-sell", "Propose additional product families the customer does not buy yet.", "sales",
        0.8,
        {"all": [
            {"signal": "growth_potential", "status": ["positive"]},
            {"state": "churn_risk", "status": ["low", "neutral"]},
            {"state": "relationship_health", "status": ["healthy", "warning"]},
        ]},
        {"any": [
            {"signal": "complaint_impact", "status": ["critical"]},
            {"signal": "complaint_impact", "evidence_ge": {"unresolved_count": 1}},
        ]},
        ["growth_potential"], ["growth_potential", "share_of_wallet", "payment_behavior"],
        "Propose a related product family, given healthy relationship and wallet headroom.",
    ),
    _def(
        "UPSELL", "Upsell", "Grow volume of products the customer already buys.", "sales",
        0.7,
        {"all": [
            {"signal": "purchase_trend", "status": ["positive", "neutral"]},
            {"signal": "profit", "status": ["positive", "neutral"]},
        ]},
        {"any": [
            {"signal": "complaint_impact", "status": ["critical"]},
        ]},
        ["purchase_trend"], ["purchase_trend", "profit"],
        "Offer higher volume or premium variants of products already purchased.",
    ),
    _def(
        "REACTIVATION", "Reactivation", "Win back a customer who has gone quiet.", "sales",
        0.8,
        {"any": [
            {"signal": "purchase_cycle", "status": ["critical"]},
        ]},
        {},
        ["purchase_cycle"], ["purchase_cycle", "profit"],
        "Reach out to re-engage a customer who is far beyond their normal purchase cycle.",
    ),
    _def(
        "PRICE_REVIEW", "Price / margin review", "Review pricing where revenue is high but margin is low.", "commercial",
        0.7,
        {"all": [
            {"signal": "profit", "status": ["warning", "critical"]},
        ]},
        {},
        ["profit", "margin_trend"], ["profit", "margin_trend"],
        "Review pricing or cost structure for a customer with weak margin.",
    ),
    _def(
        "DISCOUNT_REDUCTION", "Discount reduction", "Reduce dependence on discounts where margin is thin.", "commercial",
        0.6,
        {"all": [
            {"signal": "profit", "status": ["warning", "critical"]},
            {"signal": "offer_affinity", "status": ["positive"]},
        ]},
        {},
        ["profit"], ["profit", "offer_affinity"],
        "Reduce discount levels for a discount-responsive customer with thin margin.",
    ),
    _def(
        "PAYMENT_TERMS_REVIEW", "Payment terms review", "Review payment terms for a customer paying late.", "commercial",
        0.6,
        {"all": [
            {"signal": "payment_behavior", "status": ["warning"]},
        ]},
        {"any": [
            {"signal": "payment_behavior", "status": ["critical"]},
        ]},
        ["payment_behavior"], ["payment_behavior"],
        "Review payment terms with a customer whose payment is slipping.",
    ),
    _def(
        "CREDIT_REVIEW", "Credit review", "Review credit exposure for a high payment risk customer.", "collection",
        0.8,
        {"any": [
            {"signal": "payment_behavior", "status": ["critical"]},
        ]},
        {},
        ["payment_behavior"], ["payment_behavior"],
        "Review credit limit and outstanding exposure for a high payment-risk customer.",
    ),
    _def(
        "LOYALTY_OFFER", "Loyalty offer", "Reward a healthy, high-value customer to retain them.", "sales",
        0.5,
        {"all": [
            {"state": "value", "status": ["high"]},
            {"state": "churn_risk", "status": ["low", "neutral"]},
            {"state": "relationship_health", "status": ["healthy"]},
        ]},
        {"any": [
            {"signal": "complaint_impact", "status": ["critical"]},
        ]},
        ["growth_potential"], ["profit", "churn_risk"],
        "Offer a loyalty reward to reinforce a strong, high-value relationship.",
    ),
    _def(
        "VOLUME_OFFER", "Volume offer", "Offer a volume incentive to capture wallet headroom.", "sales",
        0.6,
        {"all": [
            {"signal": "share_of_wallet", "status": ["neutral", "positive"]},
            {"signal": "growth_potential", "status": ["positive"]},
        ]},
        {"any": [
            {"signal": "complaint_impact", "status": ["critical"]},
        ]},
        ["growth_potential"], ["share_of_wallet", "growth_potential"],
        "Offer a volume incentive to grow share where headroom exists.",
    ),
    _def(
        "BUNDLE_OFFER", "Bundle offer", "Bundle complementary products for a receptive customer.", "sales",
        0.4,
        {"all": [
            {"signal": "offer_affinity", "status": ["positive"]},
            {"state": "churn_risk", "status": ["low", "neutral"]},
        ]},
        {"any": [
            {"signal": "complaint_impact", "status": ["critical"]},
        ]},
        ["growth_potential"], ["offer_affinity", "growth_potential"],
        "Bundle complementary products for a customer responsive to offers.",
    ),
    _def(
        "PRODUCT_DEVELOPMENT_FOLLOWUP", "Product development follow-up", "Follow up on an open development request.", "relationship",
        0.5,
        {"any": [
            {"signal": "dev_request", "evidence_ge": {"open_requests": 1}},
        ]},
        {},
        ["dev_request"], ["dev_request"],
        "Follow up on the customer's open product development request.",
    ),
    _def(
        "NO_ACTION", "Monitor only", "No intervention needed; keep monitoring.", "attention",
        0.0,
        {"all": []},
        {},
        [], [],
        "No action required; continue monitoring.",
    ),
]


def get_meta(action_id: str) -> dict:
    return _ACTION_META.get(action_id, {})
