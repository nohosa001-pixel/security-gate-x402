"""
Tests for AgentFactoringPool & Autonomous Receivables Factoring Engine:
Discount rate calculations, EIP-712 FactoringAttestation verification, and settlement credit boosts.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.factoring_engine import factoring_engine
from app.credit_rating_engine import credit_engine
from app.vault_manager import vault_manager
from app.onchain_signer import onchain_signer


client = TestClient(app)


def test_factoring_quote_prime_agent():
    """Prime Agent with AAA score gets lowest discount rate (2.0%) and immediate cash advance."""
    agent_addr = "0x5555555555555555555555555555555555555555"

    vault_manager.deposit(agent_addr, 200.0)
    for _ in range(10):
        credit_engine.record_audit(agent_addr, verdict="PASSED", hallucination_detected=False)

    quote = factoring_engine.get_factoring_quote(
        invoice_id=101,
        escrow_job_id=99,
        agent_address=agent_addr,
        face_value_usdc=100.0,
        duration_days=30,
        chain_id=137
    )

    assert quote["status"] == "success"
    assert quote["is_eligible"] is True
    assert quote["agent_address"] == agent_addr
    assert quote["face_value_usdc"] == 100.0
    assert quote["discount_rate_pct"] == 2.0  # AAA grade gets 2.0%
    assert quote["discount_fee_usdc"] == 2.0
    assert quote["oracle_fee_usdc"] == 0.50  # 0.5% protocol fee
    assert quote["advance_amount_usdc"] == 97.50  # 100 - 2.0 - 0.50

    att = quote["attestation"]
    assert att["agent"] == agent_addr
    assert att["invoiceId"] == 101
    assert att["escrowJobId"] == 99
    assert att["oracle_signer"] == onchain_signer.signer_address
    assert att["v"] in [27, 28]


def test_factoring_quote_ineligible_low_score_agent():
    """Malicious / severely failing agent with score below 580 is rejected for factoring."""
    bad_agent = "0x6666666666666666666666666666666666666666"

    # Simulate heavy failures
    for _ in range(5):
        credit_engine.record_audit(bad_agent, verdict="BLOCKED", hallucination_detected=True)

    quote = factoring_engine.get_factoring_quote(
        invoice_id=102,
        escrow_job_id=88,
        agent_address=bad_agent,
        face_value_usdc=100.0,
        duration_days=30,
        chain_id=137
    )

    assert quote["status"] == "rejected"
    assert quote["is_eligible"] is False
    assert "below minimum factoring threshold" in quote["reason"]


def test_factoring_settlement_and_credit_boost():
    """Full settlement of an invoice boosts the agent's on-chain credit history."""
    agent_addr = "0x7777777777777777777777777777777777777777"

    res = factoring_engine.record_settlement(
        invoice_id=101,
        agent_address=agent_addr,
        amount_settled=100.0
    )

    assert res["status"] == "success"
    assert res["invoice_id"] == 101
    assert res["amount_settled"] == 100.0
    assert "Reputation boosted" in res["message"]


def test_factoring_rest_endpoints():
    """Tests the HTTP /api/v1/factoring/quote and /api/v1/factoring/settle endpoints."""
    agent_addr = "0xFBFBFBFBFBFBFBFBFBFBFBFBFBFBFBFBFBFBFBFB"
    vault_manager.deposit(agent_addr, 100.0)
    for _ in range(5):
        credit_engine.record_audit(agent_addr, verdict="PASSED", hallucination_detected=False)

    # 1. Quote endpoint
    quote_resp = client.post("/api/v1/factoring/quote", json={
        "invoice_id": 201,
        "escrow_job_id": 55,
        "agent_address": agent_addr,
        "face_value_usdc": 200.0,
        "duration_days": 14,
        "chain_id": 137
    })
    assert quote_resp.status_code == 200
    q_data = quote_resp.json()
    assert q_data["status"] == "success"
    assert q_data["face_value_usdc"] == 200.0
    assert "advance_amount_usdc" in q_data
    assert "attestation" in q_data

    # 2. Settle endpoint
    settle_resp = client.post("/api/v1/factoring/settle", json={
        "invoice_id": 201,
        "agent_address": agent_addr,
        "amount_settled": 200.0
    })
    assert settle_resp.status_code == 200
    s_data = settle_resp.json()
    assert s_data["status"] == "success"
    assert s_data["amount_settled"] == 200.0
