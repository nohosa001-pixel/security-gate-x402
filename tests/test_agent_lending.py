"""
Tests for AgentLendingPool & Autonomous Micro-Lending Engine:
Uncollateralized credit borrowing, interest calculations, and on-chain credit certificate verification.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.lending_engine import lending_engine
from app.credit_rating_engine import credit_engine
from app.vault_manager import vault_manager
from app.onchain_signer import onchain_signer


client = TestClient(app)


def test_lending_engine_qualified_quote():
    """Prime Agent Alice qualifies for uncollateralized loan with valid EIP-712 credit certificate."""
    alice = "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"
    vault_manager.deposit(alice, 200.0)
    for _ in range(10):
        credit_engine.record_audit(alice, verdict="PASSED", hallucination_detected=False)

    quote = lending_engine.get_loan_quote(
        agent_address=alice,
        requested_amount_usdc=50.0,
        duration_days=30,
        chain_id=137
    )

    assert quote["status"] == "success"
    assert quote["is_eligible"] is True
    assert quote["requested_amount_usdc"] == 50.0
    assert quote["interest_fee_usdc"] > 0
    assert quote["total_due_usdc"] > 50.0
    assert quote["attestation"] is not None

    att = quote["attestation"]
    assert att["agent_address"] == alice
    assert att["oracle_signer"] == onchain_signer.signer_address
    assert att["v"] in [27, 28]


def test_lending_engine_rejected_quote():
    """Unproven / Low-score Agent Eve is rejected for excessive loan request."""
    eve = "0x9999999999999999999999999999999999999999"

    quote = lending_engine.get_loan_quote(
        agent_address=eve,
        requested_amount_usdc=50000.0,  # Far exceeds limit
        duration_days=30,
        chain_id=137
    )

    assert quote["status"] == "success"
    assert quote["is_eligible"] is False
    assert quote["attestation"] is None
    assert "exceeds credit limit" in quote["reason"]


def test_lending_quote_rest_endpoint():
    """Validates the HTTP /api/v1/lending/quote endpoint."""
    alice = "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"
    req_body = {
        "agent_address": alice,
        "requested_amount_usdc": 25.0,
        "duration_days": 14,
        "chain_id": 137
    }

    response = client.post("/api/v1/lending/quote", json=req_body)
    assert response.status_code == 200
    data = response.json()

    assert data["agent_address"] == alice
    assert data["requested_amount_usdc"] == 25.0
    assert "total_due_usdc" in data


def test_loan_repayment_boost():
    """Validates that repaying a loan boosts the agent's credit history."""
    alice = "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"
    res = lending_engine.record_loan_repayment(alice, loan_id=1, amount_repaid=50.2)
    assert res["status"] == "success"
    assert "reputation boosted" in res["message"].lower()
