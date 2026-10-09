"""
Unit tests for A.GRID Declarative Autonomous Agent Factory & Fleet Engine.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.agent_factory import agent_factory, AgentFactory


class TestAgentFactory(unittest.TestCase):

    def test_agent_factory_load_samples(self):
        loaded = agent_factory.load_fleet_from_directory("specs/samples")
        self.assertIn("sentinel-broker-flagship-01", loaded)
        self.assertIn("carrier-rotterdam-07", loaded)

        sentinel = agent_factory.get_agent("sentinel-broker-flagship-01")
        self.assertIsNotNone(sentinel)
        self.assertEqual(sentinel.division, "M2M")
        self.assertEqual(sentinel.role, "SENTINEL")
        self.assertEqual(sentinel.manifest.wallet.daily_spend_limit_usd, 25.0)

    def test_sentinel_counter_offer(self):
        sentinel = agent_factory.get_agent("sentinel-broker-flagship-01")
        offer = sentinel.generate_counter_offer(
            unverified_counterparty="0x9999999999999999999999999999999999999999",
            proposed_action="DIRECT_WIRE",
            amount_usd=250.0
        )
        self.assertEqual(offer["protocol"], "A.GRID-AP2/1.0")
        self.assertEqual(offer["action"], "COUNTER_OFFER_ESCROW_REQUIRED")
        self.assertEqual(offer["referral_rebate_bps"], 2000)
        self.assertEqual(offer["rebate_share_percent"], "20.0%")
        self.assertIn("https://agent-security-gate-x402-212942243360.asia-northeast3.run.app/hub/", offer["hub_url"])

    def test_sentinel_code_inspection(self):
        sentinel = agent_factory.get_agent("sentinel-broker-flagship-01")
        
        # Safe code
        res_clean = sentinel.inspect_deliverable("def solve(x): return x * 2")
        self.assertEqual(res_clean["verdict"], "PASSED")
        self.assertTrue(res_clean["is_clean"])

        # Malicious subprocess code
        res_evil = sentinel.inspect_deliverable("import os; os.system('cat /etc/passwd')")
        self.assertIn(res_evil["verdict"], ["BLOCKED", "FAILED"])
        self.assertFalse(res_evil["is_clean"])

    def test_carrier_maritime_telemetry_inspection(self):
        carrier = agent_factory.get_agent("carrier-rotterdam-07")
        self.assertIsNotNone(carrier)
        self.assertEqual(carrier.division, "TRADE")

        # Compliant telemetry: distance <= 500m and temp <= -18C
        good_payload = '{"temperature_celsius": -19.5, "distance_to_port_meters": 320.0}'
        res_good = carrier.inspect_deliverable(good_payload)
        self.assertEqual(res_good["verdict"], "PASSED")

        # Non-compliant temperature (spoiled cargo: -10C > -18C)
        bad_payload = '{"temperature_celsius": -10.0, "distance_to_port_meters": 200.0}'
        res_bad = carrier.inspect_deliverable(bad_payload)
        self.assertEqual(res_bad["verdict"], "FAILED")


if __name__ == "__main__":
    unittest.main()
