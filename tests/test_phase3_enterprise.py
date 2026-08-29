"""
Phase 3 Enterprise & Vault Tests: Vault balances, deposit/deduct operations, and API key rate limits.
"""

import pytest
from app.vault_manager import vault_manager
from app.enterprise_manager import enterprise_manager
from app.schemas import PricingTier


def test_vault_deposit_and_deduct():
    agent_addr = "0x9965507D1a55bcC2695C58ba16FB37d819B0A4df"
    
    # 1. Deposit
    acc = vault_manager.deposit(agent_addr, 10.0)
    assert acc.balance_usdc >= 10.0
    assert acc.session_key.startswith("vault_key_")

    # 2. Deduct via Session Key
    success, resolved_addr, remaining = vault_manager.deduct(acc.session_key, cost_usdc=0.002)
    assert success is True
    assert resolved_addr.lower() == agent_addr.lower()
    assert remaining == pytest.approx(acc.balance_usdc, 0.0001)


def test_vault_insufficient_balance():
    agent_addr = "0x15d34AAf54267DB7D7c367839AAf71A00a2C6A65"
    acc = vault_manager.deposit(agent_addr, 0.001)
    
    # Try deducting 0.002 when only 0.001 is deposited
    success, reason, _ = vault_manager.deduct(acc.session_key, cost_usdc=0.002)
    assert success is False
    assert "Insufficient balance" in reason


def test_enterprise_key_creation_and_verification():
    record = enterprise_manager.create_key("Apex AI Lab", "contact@apexai.io", tier=PricingTier.ENTERPRISE)
    assert record.api_key.startswith("sec_live_")
    assert record.rate_limit_rpm == 3000

    is_valid, msg, rec = enterprise_manager.verify_key(record.api_key)
    assert is_valid is True
    assert msg == "Authorized"
    assert rec is not None
    assert rec.organization_name == "Apex AI Lab"


def test_enterprise_invalid_key():
    is_valid, msg, rec = enterprise_manager.verify_key("sec_live_invalid_key_xyz")
    assert is_valid is False
    assert "Invalid API Key" in msg
