"""
Unit tests for Autonomous Clearing & Risk Mitigation Pipeline.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.autonomous_clearing_pipeline import clearing_pipeline, SettleAndDisburseRequest, IncidentClaimRequest


class TestAutonomousClearingPipeline(unittest.TestCase):

    def test_settlement_clearing_fee_split(self):
        req = SettleAndDisburseRequest(
            job_id=8801,
            gross_amount_usd=1000.0,
            employer_address="0xEmployer11111111111111111111111111111111",
            worker_address="0xWorker2222222222222222222222222222222222",
            referral_agent_address="0xReferral33333333333333333333333333333333",
            chain_id=137
        )
        res = clearing_pipeline.execute_settlement_clearing(req)
        
        self.assertEqual(res["job_id"], 8801)
        self.assertEqual(res["gross_amount_usd"], 1000.0)
        # Total fee: 1000 * 0.0025 = $2.50
        self.assertAlmostEqual(res["protocol_fee_usd"], 2.50, places=2)
        # Worker net: 1000 - 2.50 = $997.50
        self.assertAlmostEqual(res["net_to_worker_usd"], 997.50, places=2)
        # 20% rebate to referral: 2.50 * 0.20 = $0.50
        self.assertAlmostEqual(res["referral_rebate_usd"], 0.50, places=2)
        # 80% to Treasury: 2.50 * 0.80 = $2.00
        self.assertAlmostEqual(res["treasury_deposit_usd"], 2.00, places=2)
        self.assertTrue(res["clearing_tx_hash"].startswith("0x"))

    def test_incident_slashing_and_compensation(self):
        req = IncidentClaimRequest(
            job_id=8802,
            employer_address="0xEmployer11111111111111111111111111111111",
            worker_address="0xMaliciousWorker4444444444444444444444444444",
            staked_collateral_usd=200.0,
            threat_description="Fabricated temperature IoT logs, spoiled cargo.",
            risk_domain="CUSTOMS_DELAY",
            chain_id=137
        )
        res = clearing_pipeline.execute_incident_slashing_and_claim(req)
        
        self.assertEqual(res["job_id"], 8802)
        self.assertEqual(res["slashed_amount_usd"], 200.0)
        self.assertEqual(res["insurance_payout_usd"], 200.0)
        self.assertEqual(res["status"], "EMPLOYER_COMPENSATED_WORKER_SLASHED")
        self.assertTrue(res["slashing_tx_hash"].startswith("0x"))
        self.assertTrue(res["insurance_payout_tx_hash"].startswith("0x"))

    def test_telemetry(self):
        telemetry = clearing_pipeline.get_pipeline_telemetry()
        self.assertEqual(telemetry["protocol_fee_bps"], 25)
        self.assertEqual(telemetry["referral_rebate_bps"], 2000)
        self.assertGreaterEqual(telemetry["total_settlements"], 1)
        self.assertGreaterEqual(telemetry["total_incidents_handled"], 1)


if __name__ == "__main__":
    unittest.main()
