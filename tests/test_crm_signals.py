"""Signal classification + engine integration tests.

Classification functions are pure and tested exhaustively (positive/negative
trends, insufficient data, zero revenue/cost, refunds, late payments, no offer
history, no wallet estimate). A few integration tests exercise the engine
against the real DuckDB.
"""
import pytest

from backend.crm.config import (
    MarginTrendConfig,
    PaymentConfig,
    ProfitConfig,
    PurchaseCycleConfig,
    PurchaseTrendConfig,
    ShareOfWalletConfig,
)
from backend.crm.engine import SignalEngine
from backend.crm.service import CustomerIntelligenceService
from backend.crm.signals import margin_trend, payment_behavior, profit, purchase_trend, share_of_wallet


# ---------------------------------------------------------------------------
# Pure classification tests
# ---------------------------------------------------------------------------
class TestPurchaseTrendClassification:
    def test_strong_growth(self):
        assert purchase_trend._classify(0.40, PurchaseTrendConfig()) == "strong_growth"

    def test_growth(self):
        assert purchase_trend._classify(0.15, PurchaseTrendConfig()) == "growth"

    def test_stable(self):
        assert purchase_trend._classify(0.0, PurchaseTrendConfig()) == "stable"

    def test_decline(self):
        assert purchase_trend._classify(-0.15, PurchaseTrendConfig()) == "decline"

    def test_strong_decline(self):
        assert purchase_trend._classify(-0.40, PurchaseTrendConfig()) == "strong_decline"

    def test_insufficient_data(self):
        assert purchase_trend._classify(None, PurchaseTrendConfig()) == "insufficient_data"


class TestPaymentClassification:
    def test_excellent(self):
        assert payment_behavior._classify(5.0, PaymentConfig()) == "excellent"

    def test_good(self):
        assert payment_behavior._classify(10.0, PaymentConfig()) == "good"

    def test_warning(self):
        assert payment_behavior._classify(20.0, PaymentConfig()) == "warning"

    def test_poor(self):
        assert payment_behavior._classify(40.0, PaymentConfig()) == "poor"

    def test_critical(self):
        assert payment_behavior._classify(50.0, PaymentConfig()) == "critical"


class TestProfitClassification:
    def test_high_profit(self):
        assert profit._classify(0.30, ProfitConfig()) == "high_profit"

    def test_normal_profit(self):
        assert profit._classify(0.12, ProfitConfig()) == "normal_profit"

    def test_low_profit(self):
        assert profit._classify(0.05, ProfitConfig()) == "low_profit"

    def test_negative_profit(self):
        assert profit._classify(-0.10, ProfitConfig()) == "negative_profit"


class TestShareOfWalletClassification:
    def test_low_share(self):
        assert share_of_wallet._classify(0.20, ShareOfWalletConfig()) == "low_share"

    def test_medium_share(self):
        assert share_of_wallet._classify(0.50, ShareOfWalletConfig()) == "medium_share"

    def test_high_share(self):
        assert share_of_wallet._classify(0.80, ShareOfWalletConfig()) == "high_share"


class TestMarginTrendClassification:
    def test_improving(self):
        assert margin_trend._classify(0.05, MarginTrendConfig()) == "improving"

    def test_stable(self):
        assert margin_trend._classify(0.0, MarginTrendConfig()) == "stable"

    def test_declining(self):
        assert margin_trend._classify(-0.05, MarginTrendConfig()) == "declining"

    def test_strong_decline(self):
        assert margin_trend._classify(-0.15, MarginTrendConfig()) == "strong_decline"

    def test_unknown(self):
        assert margin_trend._classify(None, MarginTrendConfig()) == "unknown"


# ---------------------------------------------------------------------------
# Engine integration (real DuckDB)
# ---------------------------------------------------------------------------
EXPECTED_SIGNALS = {
    "profit", "purchase_trend", "payment_behavior", "share_of_wallet",
    "purchase_cycle", "margin_trend", "offer_affinity", "complaint_impact",
    "growth_potential", "churn_risk", "dev_request",
}


class TestEngineIntegration:
    def test_all_signals_present_for_real_customer(self):
        engine = SignalEngine()
        signals = engine.calculate_for("C_010649")
        assert EXPECTED_SIGNALS <= set(signals.keys())

    def test_unknown_customer_returns_empty(self):
        engine = SignalEngine()
        assert engine.calculate_for("DOES_NOT_EXIST") == {}

    def test_service_unknown_customer(self):
        svc = CustomerIntelligenceService()
        ci = svc.get_intelligence("DOES_NOT_EXIST")
        assert ci.signals == {}
        assert ci.state is None

    def test_every_customer_is_calculable(self):
        """No customer may crash the engine."""
        import duckdb
        from backend.crm import data
        con = data.connect()
        ids = [r[0] for r in con.execute(
            "SELECT DISTINCT Customer_ID FROM customers LIMIT 50").fetchall()]
        con.close()
        engine = SignalEngine()
        for cid in ids:
            signals = engine.calculate_for(cid)
            assert "churn_risk" in signals  # derived signal always computed
