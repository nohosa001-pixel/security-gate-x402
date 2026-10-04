"""
Tests for Universal Factoring Bridge and Parametric Insurance Pool Integration (Phase 1).
Validates on-chain claim assignments, credit scoring discounts, double-pledging prevention,
and deterministic parametric insurance claim triggers.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.credit_rating_engine import credit_engine
from app.universal_factoring_bridge import universal_factoring_bridge
from app.universal_insurance_bridge import universal_insurance_bridge
from sdk.agent_gate_sdk import UniversalEscrowClient, IndustryDomain


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_registries():
    """Clear in-memory state before each test run to ensure strict hermetic isolation."""
    universal_factoring_bridge.active_factored_jobs.clear()
    universal_insurance_bridge.active_policies.clear()


class TestUniversalFactoring:
    def test_factoring_quote_success(self, client):
        """High-credit agent receives discount factoring quote with EIP-712 attestation."""
        worker = "0x1a01000000000000000000000000000000000001"
        for _ in range(10):
            credit_engine.record_audit(worker, verdict="PASSED", hallucination_detected=False)

        res = client.post("/api/v1/escrow/universal/factor/quote", json={
            "job_id": "UF-JOB-1001",
            "agent_address": worker,
            "face_value_usdc": 10000.0,
            "duration_days": 14,
            "chain_id": 137
        })
        assert res.status_code == 200, res.text
        data = res.json()
        assert data["job_id"] == "UF-JOB-1001"
        assert data["grade"] in ["AAA", "AA", "A", "BBB"]
        assert data["is_eligible"] is True
        assert data["face_value_usdc"] == 10000.0
        assert data["advance_amount_usdc"] > 0
        assert data["factoring_pool_address"] == "0xd0Aa4Aed2AeDE14611B53C3e93CF784F3Fe05BB0"
        assert "attestation" in data
        assert data["attestation"]["full_signature"].startswith("0x") or len(data["attestation"]["full_signature"]) == 130

    def test_factoring_quote_rejects_low_credit_agent(self, client):
        """Risky agent with severe hallucinations is rejected for factoring advance."""
        risky_worker = "0x1a02000000000000000000000000000000000002"
        # Seed low credit rating (multiple severe hallucinations)
        for _ in range(10):
            credit_engine.record_audit(risky_worker, verdict="BLOCKED", hallucination_detected=True)

        res = client.post("/api/v1/escrow/universal/factor/quote", json={
            "job_id": "UF-JOB-LOW-CREDIT",
            "agent_address": risky_worker,
            "face_value_usdc": 5000.0,
            "duration_days": 14,
            "chain_id": 137
        })
        assert res.status_code == 400
        assert "below minimum factoring threshold" in res.json()["detail"]

    def test_factoring_execute_and_prevent_double_pledging(self, client):
        """Executes claim assignment and blocks double-pledging the same escrow job."""
        worker = "0x1a03000000000000000000000000000000000003"
        for _ in range(10):
            credit_engine.record_audit(worker, verdict="PASSED", hallucination_detected=False)

        # 1. Quote
        q_res = client.post("/api/v1/escrow/universal/factor/quote", json={
            "job_id": "UF-JOB-DOUBLE-TEST",
            "agent_address": worker,
            "face_value_usdc": 8000.0,
            "duration_days": 14,
            "chain_id": 8453
        })
        assert q_res.status_code == 200, q_res.text
        quote = q_res.json()
        invoice_id = quote["invoice_id"]
        advance_usdc = quote["advance_amount_usdc"]

        # 2. Execute assignment
        exec_res = client.post("/api/v1/escrow/universal/factor/execute", json={
            "invoice_id": invoice_id,
            "job_id": "UF-JOB-DOUBLE-TEST",
            "agent_address": worker,
            "face_value_usdc": 8000.0,
            "advance_amount_usdc": advance_usdc,
            "chain_id": 8453
        })
        assert exec_res.status_code == 200, exec_res.text
        assigned = exec_res.json()
        assert assigned["status"] == "PLEDGED"
        assert assigned["assigned_recipient"] == "0x6418f408cFf03F862D7691f01fAb00a895E6aB93"

        # 3. Second execution attempt must fail (double-pledge block)
        dup_exec = client.post("/api/v1/escrow/universal/factor/execute", json={
            "invoice_id": invoice_id,
            "job_id": "UF-JOB-DOUBLE-TEST",
            "agent_address": worker,
            "face_value_usdc": 8000.0,
            "advance_amount_usdc": advance_usdc,
            "chain_id": 8453
        })
        assert dup_exec.status_code == 400
        assert "already factored and active" in dup_exec.json()["detail"]

        # 4. New quote for the same job should also be blocked
        dup_quote = client.post("/api/v1/escrow/universal/factor/quote", json={
            "job_id": "UF-JOB-DOUBLE-TEST",
            "agent_address": worker,
            "face_value_usdc": 8000.0,
            "duration_days": 14,
            "chain_id": 8453
        })
        assert dup_quote.status_code == 400
        assert "already factored and pledged" in dup_quote.json()["detail"]

    def test_universal_escrow_settlement_resolves_factoring(self, client):
        """When Universal Escrow settles, the factoring advance is marked repaid and score increases."""
        worker = "0x1a04000000000000000000000000000000000004"
        for _ in range(10):
            credit_engine.record_audit(worker, verdict="PASSED", hallucination_detected=False)

        # Factor the job
        q_res = client.post("/api/v1/escrow/universal/factor/quote", json={
            "job_id": "UF-JOB-SETTLE-SYNC",
            "agent_address": worker,
            "face_value_usdc": 10000.0,
            "duration_days": 14,
            "chain_id": 137
        })
        assert q_res.status_code == 200, q_res.text
        quote = q_res.json()
        client.post("/api/v1/escrow/universal/factor/execute", json={
            "invoice_id": quote["invoice_id"],
            "job_id": "UF-JOB-SETTLE-SYNC",
            "agent_address": worker,
            "face_value_usdc": 10000.0,
            "advance_amount_usdc": quote["advance_amount_usdc"],
            "chain_id": 137
        })

        # Settle the Universal Escrow
        settle_res = client.post("/api/v1/escrow/universal/settle", json={
            "job_id": "UF-JOB-SETTLE-SYNC",
            "domain": 0,
            "recipients": [{"recipient": "0xd0Aa4Aed2AeDE14611B53C3e93CF784F3Fe05BB0", "amount": 10000.0}],
            "truth_payload": "Port arrival verified",
            "attestation": {
                "jobId": "UF-JOB-SETTLE-SYNC",
                "verdict": "PASSED",
                "expiresAt": 1890000000,
                "signature": "0x123456"
            },
            "chain_id": 137
        })
        assert settle_res.status_code == 200, settle_res.text
        data = settle_res.json()
        assert data["factoring_settled"] is True
        assert data["factoring_details"]["status"] == "SETTLED"
        assert data["factoring_details"]["face_value_recovered"] == 10000.0


class TestUniversalParametricInsurance:
    def test_parametric_insurance_quote_success(self, client):
        """Worker requests parametric insurance quote for maritime customs delay."""
        worker = "0x2b01000000000000000000000000000000000001"
        for _ in range(5):
            credit_engine.record_audit(worker, verdict="PASSED", hallucination_detected=False)

        res = client.post("/api/v1/escrow/universal/insure/quote", json={
            "job_id": "INS-JOB-2001",
            "agent_address": worker,
            "beneficiary_address": worker,
            "coverage_amount_usdc": 20000.0,
            "risk_domain": "CUSTOMS_DELAY",
            "duration_days": 30,
            "chain_id": 137
        })
        assert res.status_code == 200, res.text
        data = res.json()
        assert data["job_id"] == "INS-JOB-2001"
        assert data["risk_domain"] == "CUSTOMS_DELAY"
        assert data["coverage_amount_usdc"] == 20000.0
        assert data["premium_amount_usdc"] > 0
        assert data["insurance_pool_address"] == "0xE67F4BC75B11dBb3ef2C9Ad1848B4b193c2c69C6"
        assert "quote" in data
        assert data["quote"]["full_signature"].startswith("0x") or len(data["quote"]["full_signature"]) == 130

    def test_parametric_insurance_trigger_payout_breach(self, client):
        """Telemetry exceeds threshold, triggering immediate parametric insurance payout."""
        worker = "0x2b02000000000000000000000000000000000002"
        # 1. Quote
        q_res = client.post("/api/v1/escrow/universal/insure/quote", json={
            "job_id": "INS-JOB-BREACH",
            "agent_address": worker,
            "beneficiary_address": worker,
            "coverage_amount_usdc": 10000.0,
            "risk_domain": "CUSTOMS_DELAY",
            "duration_days": 30,
            "chain_id": 137
        })
        assert q_res.status_code == 200, q_res.text
        quote = q_res.json()
        policy_id = quote["policy_id"]

        # 2. Trigger with metric_value = 60.5 hours (> 48 threshold)
        trig_res = client.post("/api/v1/escrow/universal/insure/trigger", json={
            "job_id": "INS-JOB-BREACH",
            "policy_id": policy_id,
            "claimant_address": worker,
            "trigger_event": "CUSTOMS_DELAY",
            "metric_value": 60.5,
            "threshold_value": 48.0,
            "incident_proof_hash": "0x" + "b" * 64,
            "chain_id": 137
        })
        assert trig_res.status_code == 200, trig_res.text
        claim = trig_res.json()
        assert claim["status"] == "APPROVED"
        assert claim["payout_approved"] is True
        assert claim["payout_amount_usdc"] == 10000.0
        assert "claim_attestation" in claim
        assert claim["claim_attestation"]["claimant"] == worker

        # 3. Repeated claim on settled policy must be rejected
        dup_trig = client.post("/api/v1/escrow/universal/insure/trigger", json={
            "job_id": "INS-JOB-BREACH",
            "policy_id": policy_id,
            "claimant_address": worker,
            "trigger_event": "CUSTOMS_DELAY",
            "metric_value": 70.0,
            "threshold_value": 48.0,
            "incident_proof_hash": "0x" + "b" * 64,
            "chain_id": 137
        })
        assert dup_trig.status_code == 400
        assert "already settled" in dup_trig.json()["detail"]

    def test_parametric_insurance_trigger_no_breach(self, client):
        """Telemetry within safe threshold results in claim rejection."""
        worker = "0x2b03000000000000000000000000000000000003"
        q_res = client.post("/api/v1/escrow/universal/insure/quote", json={
            "job_id": "INS-JOB-SAFE",
            "agent_address": worker,
            "beneficiary_address": worker,
            "coverage_amount_usdc": 5000.0,
            "risk_domain": "PORT_CONGESTION",
            "duration_days": 30,
            "chain_id": 137
        })
        assert q_res.status_code == 200, q_res.text
        policy_id = q_res.json()["policy_id"]

        # Trigger with delay = 24.0 hours (< 72 threshold)
        trig_res = client.post("/api/v1/escrow/universal/insure/trigger", json={
            "job_id": "INS-JOB-SAFE",
            "policy_id": policy_id,
            "claimant_address": worker,
            "trigger_event": "PORT_CONGESTION",
            "metric_value": 24.0,
            "threshold_value": 72.0,
            "incident_proof_hash": "0x" + "c" * 64,
            "chain_id": 137
        })
        assert trig_res.status_code == 200, trig_res.text
        claim = trig_res.json()
        assert claim["status"] == "REJECTED"
        assert claim["payout_approved"] is False
        assert "threshold not reached" in claim["reason"].lower()


class TestUniversalEscrowClientSDK:
    def test_sdk_factoring_and_insurance_flow(self):
        """Validates that the UniversalEscrowClient SDK methods operate cleanly."""
        sdk_client = UniversalEscrowClient(chain_id=137, app=app)
        worker = "0x3c01000000000000000000000000000000000001"
        for _ in range(10):
            credit_engine.record_audit(worker, verdict="PASSED", hallucination_detected=False)

        # 1. SDK Factoring Quote
        f_quote = sdk_client.get_factoring_quote(
            job_id="SDK-JOB-3001",
            worker_address=worker,
            escrow_amount_usdc=15000.0,
            duration_days=14,
            domain=IndustryDomain.TRADE_MARITIME
        )
        assert f_quote["job_id"] == "SDK-JOB-3001"
        assert f_quote["advance_amount_usdc"] > 0
        invoice_id = f_quote["invoice_id"]
        advance_usdc = f_quote["advance_amount_usdc"]

        # 2. SDK Factoring Execute
        f_exec = sdk_client.execute_factoring_advance(
            job_id="SDK-JOB-3001",
            invoice_id=invoice_id,
            worker_address=worker,
            face_value_usdc=15000.0,
            advance_amount_usdc=advance_usdc
        )
        assert f_exec["status"] == "PLEDGED"

        # 3. SDK Parametric Insurance Quote
        ins_quote = sdk_client.get_parametric_insurance_quote(
            job_id="SDK-JOB-3001",
            worker_address=worker,
            coverage_amount_usdc=5000.0,
            risk_domain="PORT_CONGESTION",
            duration_days=30
        )
        assert ins_quote["premium_amount_usdc"] > 0
        policy_id = ins_quote["policy_id"]

        # 4. SDK Parametric Claim Trigger
        ins_claim = sdk_client.trigger_parametric_claim(
            job_id="SDK-JOB-3001",
            policy_id=policy_id,
            claimant_address=worker,
            trigger_event="PORT_CONGESTION",
            metric_value=72.0,
            threshold_value=48.0
        )
        assert ins_claim["status"] == "APPROVED"
        assert ins_claim["payout_approved"] is True
        assert ins_claim["payout_amount_usdc"] == 5000.0
