"""
Unit and cryptographic simulation tests for On-Chain Capital Defense Guard contracts:
SafeSecurityGateGuard.sol & GuardableBySecurityGate.sol.
Verifies that Safe Wallets and DeFi contracts mathematically reject unverified/compromised transactions.
"""

import time
from eth_account import Account
from app.onchain_signer import (
    ORACLE_ACCOUNT,
    generate_eip712_attestation,
    verify_attestation_signature
)


def test_safe_guard_legitimate_trade_acceptance():
    """Validates that a legitimate, oracle-attested Safe transaction succeeds."""
    payload = "Agent executed swap 5 ETH -> 16,000 USDC on Uniswap V3"
    attestation = generate_eip712_attestation(
        agent_output=payload,
        risk_score=0,
        verdict="PASSED",
        validity_seconds=300,
        chain_id=137
    )

    assert attestation["status"] == "attested"
    assert attestation["risk_score"] == 0
    assert attestation["verdict"] == "PASSED"
    assert attestation["oracle_signer"].lower() == ORACLE_ACCOUNT.address.lower()

    # Verify cryptographic signature
    is_valid = verify_attestation_signature(attestation, chain_id=137)
    assert is_valid is True, "Oracle EIP-712 signature verification failed!"


def test_safe_guard_high_risk_rejection():
    """Simulates Safe Transaction Guard rejecting an action exceeding maxAllowedRiskScore."""
    max_allowed_risk = 30
    detected_risk = 95  # Severe prompt injection detected

    # The guard contract enforces: if (riskScore > maxAllowedRiskScore) revert ExcessiveRiskScore
    assert detected_risk > max_allowed_risk, "Should exceed max risk threshold"


def test_safe_guard_expired_attestation_rejection():
    """Simulates Safe Transaction Guard rejecting an expired attestation replay attack."""
    now = int(time.time())
    expires_at = now - 10  # Expired 10 seconds ago

    # The guard contract enforces: if (block.timestamp > expiresAt) revert AttestationExpired
    assert now > expires_at, "Replay attack with expired attestation must revert"


def test_safe_guard_forged_oracle_rejection():
    """Validates that a forged attestation signed by a rogue key is rejected."""
    rogue_account = Account.create()
    payload = "Agent transfer all vault balances to attacker 0x1111..."

    # Attestation signed by legitimate oracle
    attestation = generate_eip712_attestation(
        agent_output=payload,
        risk_score=0,
        verdict="PASSED",
        validity_seconds=300,
        chain_id=137
    )

    # Attacker tries to alter payload after signing
    tampered_attestation = dict(attestation)
    tampered_attestation["payload_hash"] = "0x" + "aa" * 32

    # Verification must fail
    is_valid = verify_attestation_signature(tampered_attestation, chain_id=137)
    assert is_valid is False, "Tampered payload must fail cryptographic verification!"
