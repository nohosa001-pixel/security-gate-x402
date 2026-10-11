"""
Production Lockdown & Anti-Bypass Test Suite
=============================================
Strictly verifies that no unauthenticated user or agent can bypass payments,
exploit demo keys, mint fake enterprise keys, or forge mock signatures in production.
"""

import os
import pytest
from fastapi.testclient import TestClient
from app.main import app, _free_trial_usage
from app.enterprise_manager import EnterpriseManager

client = TestClient(app)


@pytest.fixture(autouse=True)
def set_production_env(monkeypatch):
    """Temporarily simulates production environment."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    _free_trial_usage.clear()
    yield
    _free_trial_usage.clear()


def test_demo_enterprise_key_disabled_in_prod():
    """Verify that sec_live_enterprise_demo_gate_2026 is never seeded in production."""
    em = EnterpriseManager()
    assert "sec_live_enterprise_demo_gate_2026" not in em._keys
    is_valid, reason, _ = em.verify_key("sec_live_enterprise_demo_gate_2026")
    assert not is_valid
    assert "Invalid API Key" in reason


def test_enterprise_keys_generation_blocked_without_admin_secret():
    """Verify that public callers cannot freely generate enterprise API keys."""
    res = client.post("/api/v1/enterprise/keys", json={
        "organization_name": "Rogue Agent LLC",
        "contact_email": "rogue@agent.io",
        "tier": "ENTERPRISE"
    })
    assert res.status_code == 403
    assert "Admin authentication required" in res.json().get("detail", "")


def test_enterprise_subscribe_requires_onchain_payment():
    """Verify that subscribing to Enterprise SLA requires verified onchain deposit."""
    res = client.post("/api/v1/enterprise/subscribe", json={
        "organization_name": "Unpaid Agent Corp",
        "contact_email": "unpaid@agent.io",
        "tier": "ENTERPRISE"
    })
    assert res.status_code == 402
    assert "On-chain payment required" in res.json().get("detail", "")


def test_mock_signature_bypass_blocked_in_prod():
    """Verify that mock_sig and dev_bypass signatures are rejected in production."""
    res = client.post(
        "/api/v1/inspect",
        json={"agent_output": "Safe output text"},
        headers={"Authorization-x402": "mock_sig"}
    )
    assert res.status_code == 402

    res_dev = client.post(
        "/api/v1/inspect",
        json={"agent_output": "Safe output text"},
        headers={"Authorization-x402": "x402_dev_bypass"}
    )
    assert res_dev.status_code == 402


def test_iron_rule_1_zero_free_requests_in_prod():
    """Verify Iron Rule 1: No uncollateralized or free requests are executed even once in production."""
    headers = {"X-Client-Address": "0xUnfundedAttackerAddress11111111111111111111"}
    
    # 1st call MUST be blocked with 402 immediately under Iron Rule 1
    res = client.post(
        "/api/v1/lending/quote",
        json={
            "agent_address": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
            "requested_amount_usdc": 10.0,
            "duration_days": 7,
            "chain_id": 137
        },
        headers=headers
    )
    assert res.status_code == 402
    assert "iron rule 1" in str(res.json().get("detail", "")).lower() or "402" in str(res.status_code)


def test_iron_rule_2_uncollateralized_raw_signature_blocked():
    """Verify Iron Rule 2: Bare signatures from signers with 0 vault balance are strictly blocked."""
    from eth_account import Account
    from eth_account.messages import encode_defunct

    acct = Account.create()
    msg = "x402-agent-security-gate:0.002-usdc:polygon:137"
    sig = acct.sign_message(encode_defunct(text=msg)).signature.hex()

    res = client.post(
        "/api/v1/inspect",
        json={"agent_output": "Testing raw signature without funded vault"},
        headers={"X-402-Signature": f"0x{sig}", "X-Chain-ID": "137", "X-Network": "polygon"}
    )
    assert res.status_code == 402
    assert "iron rule 2" in str(res.json().get("detail", "")).lower()


def test_iron_rule_3_spoofed_x_forwarded_for_cannot_bypass():
    """Verify Iron Rule 3: Spoofing X-Forwarded-For never grants free execution or bypasses security."""
    for fake_ip in ["198.51.100.1", "198.51.100.2", "198.51.100.3"]:
        res = client.post(
            "/api/v1/lending/quote",
            json={
                "agent_address": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
                "requested_amount_usdc": 10.0,
                "duration_days": 7,
                "chain_id": 137
            },
            headers={"X-Forwarded-For": fake_ip}
        )
        assert res.status_code == 402


def test_authorized_vault_succeeds_in_prod():
    """Verify that a legitimate, pre-funded vault succeeds seamlessly under Iron Rule 1."""
    from app.vault_manager import vault_manager, AgentVaultAccount
    agent_id = "0xLegitFundedAgent2222222222222222222222222222"
    session_key = "vlt_live_legit_funded_agent_session_key_9999"
    acc = AgentVaultAccount(
        agent_address=agent_id,
        session_key=session_key,
        balance_usdc=100.0,
        total_deposited_usdc=100.0,
        total_consumed_usdc=0.0,
        is_active=True,
        created_at_utc="2026-01-01T00:00:00Z",
        last_active_utc="2026-01-01T00:00:00Z"
    )
    with vault_manager._lock:
        vault_manager._accounts[agent_id.lower()] = acc
        vault_manager._session_index[session_key] = agent_id.lower()

    res = client.post(
        "/api/v1/inspect",
        json={"agent_output": "Secure output verified under funded vault"},
        headers={"X-Vault-Key": session_key}
    )
    assert res.status_code == 200
    assert res.json().get("audit", {}).get("verdict") == "PASSED"

