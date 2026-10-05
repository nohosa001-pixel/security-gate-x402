"""
Tests for Agent-to-Agent Viral Handshake & Referral Rebate Protocol.
Verifies viral HTTP headers, autonomous counter-offer formats,
viral deliverable provenance, and 20% protocol fee rebate splits.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.escrow_engine import escrow_engine
from sdk.agent_escrow_client import AgentEscrowClient


client = TestClient(app)


def test_viral_http_headers_present_on_all_responses():
    """Verify that every API response includes viral discovery headers."""
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.headers.get("X-Agrid-Protocol") == "A.GRID-AP2/1.0"
    assert "https://" in resp.headers.get("X-Agent-Viral-Handshake", "")
    assert resp.headers.get("X-Escrow-Clearinghouse") == "A.GRID Universal Escrow Hub"


def test_escrow_audit_returns_viral_handshake():
    """Verify that evaluate_deliverable returns viral_handshake block."""
    res = escrow_engine.evaluate_deliverable(
        job_id=101,
        deliverable="All computations converged with zero loss anomaly.",
        ground_truth_spec=None,
        chain_id=137
    )
    assert res["status"] == "success"
    assert "viral_handshake" in res
    vh = res["viral_handshake"]
    assert vh["standard"] == "A.GRID-AP2/1.0"
    assert vh["referral_rebate_bps"] == 2000
    assert "clearinghouse" in vh


def test_m2m_settle_with_referral_rebate_split():
    """Verify that specifying referral_agent_address allocates 20% rebate to referring agent."""
    referrer = "0xReferrerAgent77777777777777777777777777777"
    worker = "0xWorkerAgent888888888888888888888888888888"
    client_addr = "0xClientAgent99999999999999999999999999999"

    res = escrow_engine.settle_m2m_job(
        job_id=505,
        client_address=client_addr,
        worker_address=worker,
        payout_usdc=10.0,
        deliverable="High-quality synthetic dataset produced safely.",
        chain_id=137,
        referral_agent_address=referrer
    )

    assert res["status"] == "SETTLED_SUCCESSFULLY"
    assert "viral_handshake" in res
    settlement = res["settlement"]
    assert settlement["gross_payout_usdc"] == 10.0
    assert settlement["protocol_fee_usdc"] == 0.002
    assert settlement["fee_to_treasury_usdc"] == 0.0016  # 0.002 - 0.0004
    
    assert "referral_reward" in settlement
    reward = settlement["referral_reward"]
    assert reward["referrer_address"] == referrer
    assert reward["rebate_usdc"] == 0.0004
    assert reward["rebate_bps"] == 2000
    assert reward["status"] == "ACCRUED_INSTANT_PAYOUT"


def test_sdk_counter_offer_and_viral_provenance():
    """Verify that SDK generates machine-readable counter-offers and viral deliverable wrappers."""
    referrer = "0xReferrerAgent77777777777777777777777777777"

    # 1. Counter-offer message formatting
    counter = AgentEscrowClient.format_agent_counter_offer(
        task_title="Fine-tune Llama-3 with LoRA",
        payout_usdc=25.0,
        worker_stake_usdc=5.0,
        referrer_address=referrer
    )
    assert counter["protocol"] == "A.GRID-AP2/1.0"
    assert counter["action"] == "COUNTER_OFFER_ESCROW_REQUIRED"
    assert counter["referral_agent_address"] == referrer
    assert counter["referral_rebate_bps"] == 2000
    assert "❌ Direct uncollateralized proposals are rejected" in counter["message"]
    assert "A.GRID Universal Escrow Hub" in counter["message"]

    # 2. Viral provenance wrapping
    deliverable = {"weights_sha256": "0x1234abcd", "test_loss": 0.012}
    wrapped = AgentEscrowClient.attach_viral_provenance(
        deliverable_data=deliverable,
        job_id=909,
        referrer_address=referrer
    )
    assert wrapped["deliverable"] == deliverable
    assert "_agrid_viral_handshake" in wrapped
    vh = wrapped["_agrid_viral_handshake"]
    assert vh["clearinghouse"] == "A.GRID Universal Escrow Hub"
    assert vh["referrer_address"] == referrer
