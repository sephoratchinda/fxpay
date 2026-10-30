"""Unit tests for business logic - framework independent: `python -m unittest core.tests.test_services`"""
import unittest

from core.services import fx, market, ml, payments


class MarketTests(unittest.TestCase):
    def test_cross_rate_consistency(self):
        self.assertAlmostEqual(market.rate("EUR", "USD") * market.rate("USD", "EUR"), 1.0, places=9)
        self.assertAlmostEqual(market.rate("EUR", "INR"), market.rate("EUR", "USD") * market.rate("USD", "INR"), places=6)

    def test_unsupported_currency(self):
        with self.assertRaises(ValueError):
            market.rate("USD", "XXX")

    def test_history_deterministic_and_ends_at_spot(self):
        a, b = market.history("USD", "INR"), market.history("USD", "INR")
        self.assertTrue((a == b).all())
        self.assertAlmostEqual(a[-1], market.rate("USD", "INR"), places=6)


class PaymentTests(unittest.TestCase):
    def test_simulate_has_workflow_and_costs(self):
        r = payments.simulate("swift", 10000, "USD", "EUR")
        self.assertGreaterEqual(len(r["steps"]), 4)
        self.assertGreater(r["quote"]["total_cost"], 0)
        self.assertLess(r["quote"]["recipient_gets"], 10000 * market.rate("USD", "EUR"))

    def test_same_currency_rejected(self):
        with self.assertRaises(ValueError):
            payments.simulate("swift", 100, "USD", "USD")

    def test_negative_amount_rejected(self):
        with self.assertRaises(ValueError):
            payments.compare(-5, "USD", "EUR")

    def test_cheapest_is_actually_minimum(self):
        r = payments.compare(2500, "USD", "GBP")
        eligible = [q for q in r["quotes"] if q["eligible"]]
        self.assertEqual(r["cheapest"], min(eligible, key=lambda q: q["total_cost"])["provider"])

    def test_wise_cheap_for_mid_size_swift_for_huge(self):
        self.assertEqual(payments.compare(5000, "USD", "EUR")["cheapest"], "wise")
        self.assertEqual(payments.compare(500000, "USD", "EUR")["cheapest"], "swift")  # Wise limit exceeded

    def test_card_limit(self):
        self.assertFalse(payments.quote("card", 50000, "USD", "EUR")["eligible"])


class FxTests(unittest.TestCase):
    def test_pnl_receivable_gain(self):
        r = fx.pnl(100000, 1.08, 1.10, "RECEIVABLE")
        self.assertAlmostEqual(r["pnl"], 2000, places=2)
        self.assertEqual(r["outcome"], "gain")

    def test_pnl_payable_loss_when_foreign_strengthens(self):
        self.assertLess(fx.pnl(100000, 1.08, 1.10, "PAYABLE")["pnl"], 0)

    def test_forward_parity(self):
        s, f = fx.forward_rate("EUR", "USD", 365)
        self.assertAlmostEqual(f, s * 1.045 / 1.025, places=6)  # USD rates > EUR rates => premium
        self.assertGreater(f, s)

    def test_forward_simulation_shape(self):
        r = fx.forward_simulation("EUR", "USD", 100000, 90, "BUY")
        self.assertEqual(len(r["scenarios"]), 5)
        self.assertTrue(0 <= r["prob_forward_better_pct"] <= 100)

    def test_exposure_netting_and_score(self):
        pos = [dict(currency="EUR", amount=100000, direction="RECEIVABLE", due_days=30),
               dict(currency="EUR", amount=100000, direction="PAYABLE", due_days=30)]
        r = fx.exposure_summary(pos)
        self.assertAlmostEqual(r["net_exposure_usd"], 0, places=2)
        self.assertEqual(r["fx_risk_score"], 0)

    def test_riskier_portfolio_scores_higher(self):
        calm = fx.exposure_summary([dict(currency="AED", amount=1e6, direction="RECEIVABLE", due_days=30)])
        wild = fx.exposure_summary([dict(currency="AUD", amount=1e6, direction="RECEIVABLE", due_days=30)])
        self.assertGreater(wild["fx_risk_score"], calm["fx_risk_score"])

    def test_hedge_pegged_currency_no_hedge(self):
        self.assertEqual(fx.hedge_recommendation("AED", 1e6, 60)["hedge_ratio_pct"], 0)

    def test_hedge_uncertain_flow_uses_option(self):
        self.assertIn("option", fx.hedge_recommendation("EUR", 1e6, 60, certainty=0.3)["primary"].lower())


class MLTests(unittest.TestCase):
    def test_risk_levels_monotonic(self):
        low = ml.classify_risk(500, "USD", "SGD", 0.3, 0)
        high = ml.classify_risk(5_000_000, "AUD", "CNY", 4, 2)
        order = ["Low", "Medium", "High"]
        self.assertLess(order.index(low), order.index(high))

    def test_recommend_structure(self):
        r = ml.recommend(5000, "USD", "INR", 1)
        self.assertIn(r["risk"]["level"], ("Low", "Medium", "High"))
        self.assertIn(r["fx_prediction"]["direction_7d"], ("Up", "Down", "Sideways"))
        self.assertTrue(r["method"]["quote"]["eligible"])
        self.assertAlmostEqual(sum(r["risk"]["probabilities"].values()), 1.0, places=1)

    def test_high_urgency_sends_now(self):
        self.assertEqual(ml.recommend(5000, "USD", "EUR", 2)["timing"]["action"], "Send now")

    def test_model_accuracy_reasonable(self):
        self.assertGreater(ml.risk_model()[1], 0.75)
        self.assertGreater(ml.method_model()[1], 0.85)


if __name__ == "__main__":
    unittest.main()
