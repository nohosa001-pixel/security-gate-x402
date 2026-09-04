"""
Tests for AgentInsurancePool & Autonomous Malpractice / Liability Insurance Engine:
Actuarial quote calculations, EIP-712 policy attestation, and automated claim adjudication.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.insurance_engine import insurance_engine
from app.credit_rating_engine import credit_engine
from app.vault_manager import vault_manager
from app.onchain_signer import onchain_signer


client = TestClient(app)


def test_insurance_quote_prime_agent():
    """Prime Agent with AAA score gets lowest premium rate and valid EIP-712 PolicyQuote."""
    agent_addr = "0x1111111111111111111111111111111111111111"
    beneficiary = "0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC"

    vault_manager.deposit(agent_addr, 200.0)
    for _ in range(10):
        credit_engine.record_audit(agent_addr, verdict="PASSED", hallucination_detected=False)

    quote = insurance_engine.get_policy_quote(
        agent_address=agent_addr,
        beneficiary_address=beneficiary,
        coverage_amount_usdc=500.0,
        duration_days=30,
        chain_id=137
    )

    assert quote["status"] == "success"
    assert quote["agent_address"] == agent_addr
    assert quote["coverage_amount_usdc"] == 500.0
    assert quote["annual_premium_rate_pct"] <= 2.5  # AAA/AA tier gets low rate
    assert quote["premium_amount_usdc"] > 0
    assert quote["oracle_fee_usdc"] > 0
    assert quote["total_cost_usdc"] == round(quote["premium_amount_usdc"] + quote["oracle_fee_usdc"], 4)

    att = quote["attestation"]
    assert att["agent"] == agent_addr
    assert att["beneficiary"] == beneficiary
    assert att["oracle_signer"] == onchain_signer.signer_address
    assert att["v"] in [27, 28]


def test_insurance_quote_unproven_agent():
    """Unproven / High-risk Agent pays higher risk-adjusted premium rate."""
    risky_agent = "0x8888888888888888888888888888888888888888"
    beneficiary = "0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC"

    for _ in range(3):
        credit_engine.record_audit(risky_agent, verdict="BLOCKED", hallucination_detected=True)

    quote = insurance_engine.get_policy_quote(
        agent_address=risky_agent,
        beneficiary_address=beneficiary,
        coverage_amount_usdc=500.0,
        duration_days=30,
        chain_id=137
    )

    assert quote["status"] == "success"
    assert quote["annual_premium_rate_pct"] >= 6.5  # High risk rate
    assert quote["premium_amount_usdc"] > 0


def test_claim_adjudication_and_credit_penalty():
    """Faulty agent suffering an exploit causes claim adjudication and receives credit penalty."""
    rogue_agent = "0x9999999999999999999999999999999999999999"
    claimant = "0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC"

    initial_score = credit_engine.compute_credit_score(rogue_agent)["credit_score"]

    claim_res = insurance_engine.adjudicate_claim(
        policy_id=1,
        agent_address=rogue_agent,
        claimant_address=claimant,
        claim_amount_usdc=100.0,
        incident_description="Jailbreak exploit leading to unauthorized fund drainage",
        chain_id=137
    )

    assert claim_res["status"] == "success"
    assert claim_res["policy_id"] == 1
    assert claim_res["claimant"] == claimant
    assert claim_res["claim_amount_usdc"] == 100.0
    assert claim_res["incident_hash"].startswith("0x")
    assert claim_res["attestation"]["oracle_signer"] == onchain_signer.signer_address
    assert claim_res["attestation"]["v"] in [27, 28]

    # Verify score was penalized
    assert claim_res["agent_updated_credit_score"] < initial_score


def test_insurance_rest_endpoints():
    """Tests the HTTP /api/v1/insurance/quote and /api/v1/insurance/claim endpoints."""
    agent_quote = "0x2222222222222222222222222222222222222222"
    agent_claim = "0x3333333333333333333333333333333333333333"
    beneficiary = "0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC"

    # 1. Quote endpoint
    quote_resp = client.post("/api/v1/insurance/quote", json={
        "agent_address": agent_quote,
        "beneficiary_address": beneficiary,
        "coverage_amount_usdc": 300.0,
        "duration_days": 14,
        "chain_id": 137
    })
    assert quote_resp.status_code == 200
    q_data = quote_resp.json()
    assert q_data["coverage_amount_usdc"] == 300.0
    assert "attestation" in q_data

    # 2. Claim endpoint
    claim_resp = client.post("/api/v1/insurance/claim", json={
        "policy_id": 42,
        "agent_address": agent_claim,
        "claimant_address": beneficiary,
        "claim_amount_usdc": 50.0,
        "incident_description": "Data analysis pipeline hallucinated $2M metric",
        "chain_id": 137
    })
    assert claim_resp.status_code == 200
    c_data = claim_resp.json()
    assert c_data["policy_id"] == 42
    assert c_data["claim_amount_usdc"] == 50.0
    assert "attestation" in c_data
