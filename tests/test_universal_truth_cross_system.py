"""
Comprehensive Cross-System Integration & Invariant Tests for Universal Truth Escrow.
Verifies interactions, boundary safety, and synchronization with:
- Credit Rating Engine (Moody's & S&P of AI Agents)
- Sovereign RWA Treasury Engine (T-Bill backed Proof-of-Reserve)
- Anti-Exploit / Sanctions Blacklist Enforcement
- Zero Address / Malformed Address Defense
- Agent Tooling & LangChain/CrewAI Adapter (UniversalEscrowTool)
"""

import time
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.credit_rating_engine import credit_engine
from app.rwa_treasury_engine import sovereign_treasury
from sdk import UniversalEscrowTool, IndustryDomain


client = TestClient(app)


def test_cross_system_invalid_domain_rejected():
    """System Boundary: Rejects invalid industry domain (must be 0, 1, or 2)."""
    payload = {
        "job_id": "job_invalid_domain",
        "domain": 99,  # Invalid
        "recipients": [{"recipient": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8", "amount": 1000.0}],
        "truth_payload": "some proof",
        "attestation": {"jobId": "job_invalid_domain", "verdict": "PASSED", "isValid": True},
        "chain_id": 137,
        "verifying_contract": "0x5555555555555555555555555555555555555555"
    }
    resp = client.post("/api/v1/escrow/universal/settle", json=payload)
    assert resp.status_code == 400
    assert "Invalid domain" in resp.json()["detail"]


def test_cross_system_failed_truth_cannot_disburse():
    """Security Invariant: Cannot disburse funds if truth validation failed."""
    payload = {
        "job_id": "job_failed_truth",
        "domain": 0,
        "recipients": [{"recipient": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8", "amount": 5000.0}],
        "truth_payload": "cold chain thawed (-10C)",
        "attestation": {
            "jobId": "job_failed_truth",
            "verdict": "FAILED",
            "isValid": False
        },
        "chain_id": 137,
        "verifying_contract": "0x5555555555555555555555555555555555555555"
    }
    resp = client.post("/api/v1/escrow/universal/settle", json=payload)
    assert resp.status_code == 400
    assert "Physical truth verification failed" in resp.json()["detail"]


def test_cross_system_expired_attestation_rejected():
    """Security Invariant: Rejects expired oracle attestations."""
    payload = {
        "job_id": "job_expired",
        "domain": 2,
        "recipients": [{"recipient": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8", "amount": 2000.0}],
        "truth_payload": "valid proof but too late",
        "attestation": {
            "jobId": "job_expired",
            "verdict": "PASSED",
            "isValid": True,
            "expiresAt": int(time.time()) - 3600  # Expired 1 hour ago
        },
        "chain_id": 137,
        "verifying_contract": "0x5555555555555555555555555555555555555555"
    }
    resp = client.post("/api/v1/escrow/universal/settle", json=payload)
    assert resp.status_code == 400
    assert "expired" in resp.json()["detail"].lower()


def test_cross_system_zero_address_and_malformed_rejected():
    """Sanitization: Rejects zero address (0x0) or malformed EVM addresses."""
    # Case A: Zero Address
    payload_zero = {
        "job_id": "job_zero_addr",
        "domain": 1,
        "recipients": [{"recipient": "0x0000000000000000000000000000000000000000", "amount": 1000.0}],
        "truth_payload": "genomics ok",
        "attestation": {"jobId": "job_zero_addr", "verdict": "PASSED", "isValid": True},
        "chain_id": 137,
        "verifying_contract": "0x5555555555555555555555555555555555555555"
    }
    resp_zero = client.post("/api/v1/escrow/universal/settle", json=payload_zero)
    assert resp_zero.status_code == 400
    assert "Zero address" in resp_zero.json()["detail"]

    # Case B: Malformed address
    payload_malformed = {
        "job_id": "job_malformed",
        "domain": 1,
        "recipients": [{"recipient": "not_an_eth_address", "amount": 1000.0}],
        "truth_payload": "genomics ok",
        "attestation": {"jobId": "job_malformed", "verdict": "PASSED", "isValid": True},
        "chain_id": 137,
        "verifying_contract": "0x5555555555555555555555555555555555555555"
    }
    resp_bad = client.post("/api/v1/escrow/universal/settle", json=payload_malformed)
    assert resp_bad.status_code == 400
    assert "Invalid recipient EVM address format" in resp_bad.json()["detail"]


def test_cross_system_blacklisted_actor_blocked():
    """Anti-Exploit: Intercepts and blocks payouts to blacklisted adversarial actors."""
    bad_actor = "0xBadActorExploiter99999999999999999999999"
    credit_engine.record_exploit_attempt(bad_actor, reason="Prompt injection attempt on core vault")

    payload = {
        "job_id": "job_exploit_payout",
        "domain": 2,
        "recipients": [{"recipient": bad_actor, "amount": 10000.0}],
        "truth_payload": "BIM match 99%",
        "attestation": {"jobId": "job_exploit_payout", "verdict": "PASSED", "isValid": True},
        "chain_id": 137,
        "verifying_contract": "0x5555555555555555555555555555555555555555"
    }
    resp = client.post("/api/v1/escrow/universal/settle", json=payload)
    assert resp.status_code == 403
    assert "blacklisted" in resp.json()["detail"].lower()


def test_cross_system_credit_score_upgrade_and_treasury_sync():
    """
    Positive Feedback Loop:
    - Honest laborers & suppliers delivering truth gain on-chain FICO credit score boost.
    - Protocol toll (0.25%) automatically accrues to Sovereign RWA Treasury.
    """
    honest_worker = "0xHonestPrecastSupplier4242424242424242"
    initial_audits = credit_engine.agent_telemetry.get(honest_worker.lower(), {}).get("audits", 0)
    initial_tolls = sovereign_treasury.accumulated_tolls

    payout_amt = 80000.0
    expected_fee = payout_amt * 0.0025  # $200.00

    payload = {
        "job_id": "job_cross_system_payout",
        "domain": 2,
        "recipients": [{"recipient": honest_worker, "amount": payout_amt}],
        "truth_payload": "Concrete 35 MPa cured, LiDAR matched 99.4%",
        "attestation": {
            "jobId": "job_cross_system_payout",
            "verdict": "PASSED",
            "isValid": True,
            "expiresAt": int(time.time()) + 3600
        },
        "chain_id": 137,
        "verifying_contract": "0x5555555555555555555555555555555555555555"
    }
    resp = client.post("/api/v1/escrow/universal/settle", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "SETTLED"
    assert data["protocol_fee_usdc"] == expected_fee

    # 1. Verify Credit Rating Sync
    updated_audits = credit_engine.agent_telemetry[honest_worker.lower()]["audits"]
    assert updated_audits == initial_audits + 1

    # 2. Verify Sovereign Treasury Sync
    assert sovereign_treasury.accumulated_tolls == pytest.approx(initial_tolls + expected_fee, rel=1e-4)


def test_cross_system_universal_escrow_tool():
    """Verifies UniversalEscrowTool integration for LangChain, CrewAI, AutoGen agents."""
    import json
    tool = UniversalEscrowTool(app=app)

    # 1. Agent creates escrow
    res_create = tool.run(
        "create_escrow",
        domain="CONSTRUCTION_BUILD",
        amount_usdc=150000.0,
        truth_requirement_hash="0x" + "a" * 64,
        job_id="job_langchain_agent_001"
    )
    data_create = json.loads(res_create)
    assert data_create["status"] == "DEPOSITED"
    assert data_create["job_id"] == "job_langchain_agent_001"
    assert data_create["domain"] == "CONSTRUCTION_BUILD"

    # 2. Agent settles escrow upon verified truth
    res_settle = tool.run(
        "settle_escrow",
        job_id="job_langchain_agent_001",
        proof_data="LiDAR BIM matched 99.1%",
        recipients=[
            {"recipient": "0xSteelSubcontractor11", "amount": 90000.0},
            {"recipient": "0xConcreteSupplier22", "amount": 60000.0}
        ],
        attestation={
            "jobId": "job_langchain_agent_001",
            "verdict": "PASSED",
            "isValid": True,
            "expiresAt": int(time.time()) + 3600
        }
    )
    data_settle = json.loads(res_settle)
    assert data_settle["status"] == "SETTLED_SUCCESSFULLY"
    assert data_settle["total_disbursed_usdc"] == 150000.0
    assert data_settle["protocol_fee_usdc"] == 375.0  # 0.25% of 150k
