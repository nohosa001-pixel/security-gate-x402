"""
Unit tests for Agent Credit Scoring & DID Reputation Engine (Track 2).
"""

import pytest
from app.agent_credit_engine import agent_credit_engine


def test_top_tier_agent_credit_score():
    """ElizaOS top agent should have AAA tier and 0% collateral requirement."""
    addr = "0x71C8364737Ac3529360573e7218E66270436d65b"
    res = agent_credit_engine.calculate_credit_score(addr)

    assert res["agent_address"].lower() == addr.lower()
    assert res["credit_score"] >= 800
    assert "AAA" in res["tier"] or "AA" in res["tier"]
    assert res["required_collateral_ratio"] <= 0.25
    assert res["max_credit_limit_usdc"] >= 50000.0


def test_slashed_agent_credit_score():
    """Rogue agent with high slashing history should be Blacklisted/Subprime."""
    addr = "0xDead00000000000000000000000000000000bEEF"
    res = agent_credit_engine.calculate_credit_score(addr)

    assert res["credit_score"] == 300  # Clamped minimum
    assert "Subprime" in res["tier"] or "Blacklisted" in res["tier"]
    assert res["required_collateral_ratio"] >= 1.50
    assert res["max_credit_limit_usdc"] == 0.0


def test_eip712_credit_attestation():
    """Should issue valid cryptographically signed EIP-712 attestation."""
    addr = "0x5cC5Afa2a97599d492A3E408Fdd95fD0b520f173"
    att_res = agent_credit_engine.generate_eip712_credit_attestation(
        agent_address=addr,
        chain_id=137,
        verifying_contract="0x8ACafCEce0B1BFE140e75614b90FD1307b6f389d"
    )

    att = att_res["attestation"]
    assert att["agent"].lower() == addr.lower()
    assert att["credit_score"] >= 900
    assert att["signature"].startswith("0x")
    assert att["r"].startswith("0x")
    assert att["s"].startswith("0x")
    assert att["v"] in (27, 28)
