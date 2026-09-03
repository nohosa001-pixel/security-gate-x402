"""
Unit tests for Autonomous Agent Credit Rating Agency Oracle ("Moody's & S&P of AI Agents").
Tests quantitative credit scoring (300-850), investment grades (AAA-D),
on-chain EIP-712 credit certificates, REST endpoints, and MCP tool execution.
"""

from fastapi.testclient import TestClient
from app.main import app
from app.credit_rating_engine import credit_engine
from app.vault_manager import vault_manager
from sdk import SecurityGateClient
import pytest


def test_credit_engine_prime_institutional_agent():
    """An agent with healthy deposits and 100% clean audit history earns AAA / AA rating."""
    agent_addr = "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"
    vault_manager.deposit(agent_addr, 250.0) # $250 USDC deposit

    for _ in range(15):
        credit_engine.record_audit(agent_addr, verdict="PASSED", hallucination_detected=False)

    report = credit_engine.compute_credit_score(agent_addr)
    assert report["credit_score"] >= 750, f"Expected prime score >= 750, got {report['credit_score']}"
    assert report["grade"] in ("AAA", "AA"), f"Expected AAA or AA grade, got {report['grade']}"
    assert report["max_uncollateralized_loan_usdc"] >= 50000.0


def test_credit_engine_adversarial_downgrade_to_default():
    """An agent attempting prompt injections is immediately downgraded to Junk/Default (Grade D)."""
    bad_agent = "0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC"

    for _ in range(4):
        credit_engine.record_audit(bad_agent, verdict="BLOCKED", hallucination_detected=True)

    report = credit_engine.compute_credit_score(bad_agent)
    assert report["grade"] == "D"
    assert report["max_uncollateralized_loan_usdc"] == 0.0
    assert "Default" in report["grade_description"]


def test_credit_engine_eip712_certificate_issuance():
    """Validates that on-chain EIP-712 Credit Certificate has valid cryptographic fields."""
    agent_addr = "0x90F8bf6A479f320ead074411a4B0e7944Ea8c9C1"
    cert = credit_engine.generate_credit_certificate(agent_addr, chain_id=137)

    assert cert["status"] == "success"
    assert cert["agent_address"] == agent_addr
    assert cert["oracle_signer"].startswith("0x")
    assert cert["signature"].startswith("0x")
    assert cert["v"] in (27, 28)
    assert len(cert["r"]) == 66
    assert len(cert["s"]) == 66


def test_rest_api_credit_endpoints():
    """Tests /api/v1/credit/{agent_address} and /api/v1/credit/attestation."""
    client = TestClient(app)
    test_agent = "0x15d34AAf54267DB7D7c367839AAf71A00a2C6A65"

    # 1. Query Credit Rating
    res_rating = client.get(f"/api/v1/credit/{test_agent}")
    assert res_rating.status_code == 200
    data = res_rating.json()
    assert "credit_score" in data
    assert "grade" in data
    assert "max_uncollateralized_loan_usdc" in data

    # 2. Query Credit Attestation
    res_cert = client.post("/api/v1/credit/attestation", json={"agent_address": test_agent, "chain_id": 137})
    assert res_cert.status_code == 200
    cert_data = res_cert.json()
    assert cert_data["status"] == "success"
    assert "signature" in cert_data


def test_sdk_credit_query():
    """Tests Python SDK client.get_credit_rating() and get_credit_attestation()."""
    sdk_client = SecurityGateClient(is_dev=True, app=app)
    test_agent = "0x9965507D1a55bcC2695C58ba16FB37d819B0A4df"

    rating = sdk_client.get_credit_rating(test_agent)
    assert rating["credit_score"] >= 300

    cert = sdk_client.get_credit_attestation(test_agent, chain_id=137)
    assert cert["oracle_signer"].startswith("0x")
