"""
Unit tests for EU AI Act & Institutional Regulatory Compliance Engine (Regulation EU 2024/1689 Articles 50 & 53).
Tests compliance passport evaluation, on-chain EIP-712 certificate issuance, REST API, and SDK integration.
"""

from fastapi.testclient import TestClient
from app.main import app
from app.compliance_engine import compliance_engine
from app.credit_rating_engine import credit_engine
from app.vault_manager import vault_manager
from sdk import SecurityGateClient


def test_compliance_engine_certified_evaluation():
    """Validates that a compliant agent receives an official EU AI Act Compliance Passport."""
    agent_addr = "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"
    vault_manager.deposit(agent_addr, 100.0)

    for _ in range(5):
        credit_engine.record_audit(agent_addr, verdict="PASSED", hallucination_detected=False)

    report = compliance_engine.evaluate_compliance(agent_addr)
    assert report["is_certified"] is True
    assert report["compliance_status"] == "CERTIFIED_COMPLIANT"
    assert report["passport_id"].startswith("EU-AI-")
    assert report["audited_articles"]["article_50_transparency"]["status"] == "PASS"
    assert report["audited_articles"]["article_53_risk_mitigation"]["status"] == "PASS"
    assert report["audited_articles"]["gdpr_data_privacy"]["status"] == "PASS"


def test_compliance_engine_compromised_probation():
    """An agent with multiple prompt injection blocks fails Article 53 risk mitigation."""
    bad_agent = "0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC"

    for _ in range(4):
        credit_engine.record_audit(bad_agent, verdict="BLOCKED", hallucination_detected=True)

    report = compliance_engine.evaluate_compliance(bad_agent)
    assert report["is_certified"] is False
    assert report["compliance_status"] == "NON_COMPLIANT_PROBATION"
    assert report["audited_articles"]["article_53_risk_mitigation"]["status"] == "FAIL"


def test_compliance_onchain_attestation_signing():
    """Tests issuing an EIP-712 signed Compliance Certificate for smart contract verification."""
    agent_addr = "0x90F8bf6A479f320ead074411a4B0e7944Ea8c9C1"
    cert = compliance_engine.issue_onchain_compliance_certificate(agent_addr, chain_id=137)

    assert cert["status"] == "success"
    assert cert["agent_address"] == agent_addr
    assert cert["oracle_signer"].startswith("0x")
    assert cert["signature"].startswith("0x")
    assert cert["v"] in (27, 28)


def test_rest_api_compliance_endpoints():
    """Tests GET /api/v1/compliance/passport/{agent} and GET /api/v1/compliance/eu-ai-act."""
    client = TestClient(app)
    test_agent = "0x15d34AAf54267DB7D7c367839AAf71A00a2C6A65"

    res_passport = client.get(f"/api/v1/compliance/passport/{test_agent}")
    assert res_passport.status_code == 200
    data = res_passport.json()
    assert "passport_id" in data
    assert "regulation" in data

    res_summary = client.get("/api/v1/compliance/eu-ai-act")
    assert res_summary.status_code == 200
    summary_data = res_summary.json()
    assert "EU AI Act" in summary_data["regulation"]


def test_sdk_compliance_passport_query():
    """Tests Python SDK client.get_compliance_passport()."""
    sdk_client = SecurityGateClient(is_dev=True, app=app)
    test_agent = "0x9965507D1a55bcC2695C58ba16FB37d819B0A4df"

    passport = sdk_client.get_compliance_passport(test_agent)
    assert "passport_id" in passport
    assert "audited_articles" in passport
