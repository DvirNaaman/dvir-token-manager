import os
import unittest

from token_dashboard.pricing import load_pricing, cost_for, format_for_user

PRICING = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "pricing.json"))


class CostTests(unittest.TestCase):
    def setUp(self):
        self.p = load_pricing(PRICING)

    def _u(self, **kw):
        base = {
            "input_tokens": 0, "output_tokens": 0, "cache_read_tokens": 0,
            "cache_create_5m_tokens": 0, "cache_create_1h_tokens": 0,
        }
        base.update(kw)
        return base

    def test_known_opus_input_cost(self):
        c = cost_for("claude-opus-5", self._u(input_tokens=1_000_000), self.p)
        self.assertAlmostEqual(c["usd"], 5.00, places=4)
        self.assertFalse(c["estimated"])

    def test_known_sonnet_output_cost(self):
        c = cost_for("claude-sonnet-5", self._u(output_tokens=1_000_000), self.p)
        self.assertAlmostEqual(c["usd"], 15.00, places=4)

    def test_known_fable_output_cost(self):
        c = cost_for("claude-fable-5", self._u(output_tokens=1_000_000), self.p)
        self.assertAlmostEqual(c["usd"], 50.00, places=4)
        self.assertFalse(c["estimated"])

    def test_unknown_opus_falls_back(self):
        c = cost_for("claude-opus-9-9-experimental", self._u(input_tokens=1_000_000), self.p)
        self.assertAlmostEqual(c["usd"], 5.00, places=4)
        self.assertTrue(c["estimated"])

    def test_unknown_fable_falls_back(self):
        c = cost_for("claude-fable-9-experimental", self._u(input_tokens=1_000_000), self.p)
        self.assertAlmostEqual(c["usd"], 10.00, places=4)
        self.assertTrue(c["estimated"])

    def test_context_variant_prices_as_base_model(self):
        # Claude Code writes "claude-opus-5[1m]" into the transcript; the 1M
        # window bills at the base rate, so it must resolve exactly, not via
        # the tier guess.
        c = cost_for("claude-opus-5[1m]", self._u(input_tokens=1_000_000), self.p)
        self.assertAlmostEqual(c["usd"], 5.00, places=4)
        self.assertFalse(c["estimated"])

    def test_dated_snapshot_prices_as_base_model(self):
        # Real transcripts carry ids like claude-haiku-4-5-20251001.
        c = cost_for("claude-haiku-4-5-20251001", self._u(output_tokens=1_000_000), self.p)
        self.assertAlmostEqual(c["usd"], 5.00, places=4)
        self.assertFalse(c["estimated"])

    def test_unknown_unparseable_returns_none(self):
        c = cost_for("custom-local-model", self._u(input_tokens=9999), self.p)
        self.assertIsNone(c["usd"])

    def test_cache_read_cheaper_than_input(self):
        c_in = cost_for("claude-opus-5", self._u(input_tokens=1_000_000), self.p)
        c_cr = cost_for("claude-opus-5", self._u(cache_read_tokens=1_000_000), self.p)
        self.assertLess(c_cr["usd"], c_in["usd"])

    def test_every_model_entry_has_all_rate_fields(self):
        required = {"tier", "input", "output", "cache_read", "cache_create_5m", "cache_create_1h"}
        for name, rates in self.p["models"].items():
            self.assertTrue(required <= set(rates), f"{name} is missing {required - set(rates)}")
            self.assertIn(rates["tier"], self.p["tier_fallback"], f"{name} has an unknown tier")


class PlanFormatTests(unittest.TestCase):
    def setUp(self):
        self.p = load_pricing(PRICING)

    def test_api_plan_returns_raw(self):
        out = format_for_user(12.34, "api", self.p)
        self.assertEqual(out["display_usd"], 12.34)
        self.assertIsNone(out["subscription_usd"])

    def test_pro_plan_returns_subscription_subtitle(self):
        out = format_for_user(12.34, "pro", self.p)
        self.assertEqual(out["subscription_usd"], 20)
        self.assertIn("Pro", out["subtitle"])


if __name__ == "__main__":
    unittest.main()
