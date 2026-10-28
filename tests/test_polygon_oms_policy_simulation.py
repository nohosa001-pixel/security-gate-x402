"""
Verification and Simulation Test Suite for Polygon OMS Smart Sessions Security Policy:
SecurityGateOMSPolicy.sol (ISessionPolicy Standard).

Simulates all critical on-chain boundaries:
1. Legitimate x402 payment within budget and carrying valid Security Gate Attestation (PASSED).
2. Blocked: Payment exceeding session spending limit (e.g. 650 USDC > 500 USDC limit).
3. Blocked: Payment targeting unauthorized recipient (not whitelisted / not A.GRID Escrow Hub).
4. Blocked: Inactive or revoked session (Emergency kill-switch).
5. Blocked: Expired session time window.
6. Blocked: Missing Security Gate Attestation (Blind execution blocked).
7. Blocked: Excessive Risk Score (e.g. 95/100 prompt injection / malicious AST code).
8. Blocked: Expired Security Gate Attestation replay attack.
9. Blocked: Forged Oracle Signature signed by unauthorized key.
10. Blocked: Tampered payload / calldata parameters mismatch.
"""

import time
import pytest
from eth_account import Account
from eth_account.messages import encode_typed_data
import eth_utils
import eth_abi
from eth_abi.packed import encode_packed

from app.onchain_signer import (
    ORACLE_ACCOUNT,
    OnchainSecuritySigner
)

POLYGON_ESCROW_HUB = "0x8ACafCEce0B1BFE140e75614b90FD1307b6f389d"
MOCK_POLICY_CONTRACT = "0x1111222233334444555566667777888899990000"
CHAIN_ID = 137


def generate_oms_attestation(
    target: str,
    value: int,
    data: bytes,
    risk_score: int,
    verdict: str,
    validity_seconds: int = 300,
    signer_account: Account = ORACLE_ACCOUNT,
    verifying_contract: str = MOCK_POLICY_CONTRACT
):
    """
    Generates exact EIP-712 attestation matching SecurityGateOMSPolicy.sol
    """
    # payloadHash = keccak256(abi.encodePacked(target, value, data))
    packed_payload = encode_packed(
        ["address", "uint256", "bytes"],
        [target, value, data]
    )
    payload_hash = eth_utils.keccak(packed_payload)

    now = int(time.time())
    expires_at = now + validity_seconds

    domain_data = {
        "name": "SecurityGateOMSPolicy",
        "version": "1",
        "chainId": CHAIN_ID,
        "verifyingContract": verifying_contract
    }

    types = {
        "EIP712Domain": [
            {"name": "name", "type": "string"},
            {"name": "version", "type": "string"},
            {"name": "chainId", "type": "uint256"},
            {"name": "verifyingContract", "type": "address"}
        ],
        "SecurityAttestation": [
            {"name": "payloadHash", "type": "bytes32"},
            {"name": "riskScore", "type": "uint8"},
            {"name": "verdict", "type": "string"},
            {"name": "expiresAt", "type": "uint256"}
        ]
    }

    message_data = {
        "payloadHash": payload_hash,
        "riskScore": risk_score,
        "verdict": verdict,
        "expiresAt": expires_at
    }

    structured_data = {
        "types": types,
        "primaryType": "SecurityAttestation",
        "domain": domain_data,
        "message": message_data
    }

    signable_msg = encode_typed_data(full_message=structured_data)
    signed = signer_account.sign_message(signable_msg)

    # Encode proof as (uint8 riskScore, string verdict, uint256 attestationExpiry, bytes signature)
    proof_bytes = eth_abi.encode(
        ["uint8", "string", "uint256", "bytes"],
        [risk_score, verdict, expires_at, signed.signature]
    )

    return {
        "payload_hash": payload_hash,
        "risk_score": risk_score,
        "verdict": verdict,
        "expires_at": expires_at,
        "signature": signed.signature,
        "proof_bytes": proof_bytes,
        "signer": signer_account.address
    }


def simulate_check_user_op_policy(
    session_config: dict,
    target: str,
    value: int,
    data: bytes,
    proof_bytes: bytes,
    oracle_signer: str = ORACLE_ACCOUNT.address,
    max_allowed_risk: int = 30,
    current_time: int = None,
    verifying_contract: str = MOCK_POLICY_CONTRACT
):
    """
    Python mirror of SecurityGateOMSPolicy.checkUserOpPolicy logic.
    Returns (True, "OK") or raises ValueError with contract error name.
    """
    if current_time is None:
        current_time = int(time.time())

    # 1. Check Session State
    if not session_config.get("is_active", False):
        raise ValueError("SessionInactive")
    if current_time > session_config.get("expires_at", 0):
        raise ValueError("SessionExpired")

    # 2. Check Target Whitelist
    allowed_target = session_config.get("allowed_target")
    if allowed_target and allowed_target.lower() != target.lower():
        raise ValueError("UnauthorizedTarget")

    # 3. Check Budget Ceiling
    current_spent = session_config.get("current_spent", 0)
    max_limit = session_config.get("max_spend_limit", 0)
    if current_spent + value > max_limit:
        raise ValueError("BudgetExceeded")

    # 4. Check Security Gate Attestation
    if not proof_bytes or len(proof_bytes) == 0:
        raise ValueError("MissingSecurityAttestation")

    risk_score, verdict, attestation_expiry, signature = eth_abi.decode(
        ["uint8", "string", "uint256", "bytes"],
        proof_bytes
    )

    if current_time > attestation_expiry:
        raise ValueError("AttestationExpired")
    if risk_score > max_allowed_risk:
        raise ValueError("ExcessiveRiskScore")

    # Reconstruct EIP-712 digest
    packed_payload = encode_packed(
        ["address", "uint256", "bytes"],
        [target, value, data]
    )
    payload_hash = eth_utils.keccak(packed_payload)

    domain_data = {
        "name": "SecurityGateOMSPolicy",
        "version": "1",
        "chainId": CHAIN_ID,
        "verifyingContract": verifying_contract
    }
    types = {
        "EIP712Domain": [
            {"name": "name", "type": "string"},
            {"name": "version", "type": "string"},
            {"name": "chainId", "type": "uint256"},
            {"name": "verifyingContract", "type": "address"}
        ],
        "SecurityAttestation": [
            {"name": "payloadHash", "type": "bytes32"},
            {"name": "riskScore", "type": "uint8"},
            {"name": "verdict", "type": "string"},
            {"name": "expiresAt", "type": "uint256"}
        ]
    }
    message_data = {
        "payloadHash": payload_hash,
        "riskScore": risk_score,
        "verdict": verdict,
        "expiresAt": attestation_expiry
    }
    structured_data = {
        "types": types,
        "primaryType": "SecurityAttestation",
        "domain": domain_data,
        "message": message_data
    }
    signable_msg = encode_typed_data(full_message=structured_data)
    recovered_address = Account.recover_message(signable_msg, signature=signature)

    if recovered_address.lower() != oracle_signer.lower():
        raise ValueError("InvalidAttestationSignature")

    return True


# =========================================================================
# TEST SUITE
# =========================================================================

@pytest.fixture
def active_session():
    now = int(time.time())
    return {
        "session_key": "0x" + "a" * 64,
        "max_spend_limit": 500 * 10**6,  # 500 USDC
        "current_spent": 0,
        "expires_at": now + 86400,  # 24 hours
        "is_active": True,
        "allowed_target": POLYGON_ESCROW_HUB
    }


def test_oms_policy_happy_path(active_session):
    """Scenario 1: Legitimate top-up of 120 USDC within budget and certified clean."""
    target = POLYGON_ESCROW_HUB
    value = 120 * 10**6  # 120 USDC
    data = b"\x12\x34\x56\x78"

    attestation = generate_oms_attestation(
        target=target,
        value=value,
        data=data,
        risk_score=0,
        verdict="PASSED"
    )

    is_valid = simulate_check_user_op_policy(
        session_config=active_session,
        target=target,
        value=value,
        data=data,
        proof_bytes=attestation["proof_bytes"]
    )
    assert is_valid is True, "Legitimate OMS agent payment should pass"


def test_oms_policy_budget_exceeded(active_session):
    """Scenario 2: Agent attempts to pay 650 USDC when limit is 500 USDC."""
    target = POLYGON_ESCROW_HUB
    value = 650 * 10**6  # 650 USDC
    data = b"\x12\x34\x56\x78"

    attestation = generate_oms_attestation(
        target=target,
        value=value,
        data=data,
        risk_score=0,
        verdict="PASSED"
    )

    with pytest.raises(ValueError, match="BudgetExceeded"):
        simulate_check_user_op_policy(
            session_config=active_session,
            target=target,
            value=value,
            data=data,
            proof_bytes=attestation["proof_bytes"]
        )


def test_oms_policy_unauthorized_target(active_session):
    """Scenario 3: Agent attempts to send payment to an unapproved recipient."""
    attacker_contract = "0x9999999999999999999999999999999999999999"
    value = 50 * 10**6
    data = b"\x00"

    attestation = generate_oms_attestation(
        target=attacker_contract,
        value=value,
        data=data,
        risk_score=0,
        verdict="PASSED"
    )

    with pytest.raises(ValueError, match="UnauthorizedTarget"):
        simulate_check_user_op_policy(
            session_config=active_session,
            target=attacker_contract,
            value=value,
            data=data,
            proof_bytes=attestation["proof_bytes"]
        )


def test_oms_policy_revoked_session(active_session):
    """Scenario 4: Team toggled the emergency kill-switch."""
    active_session["is_active"] = False

    target = POLYGON_ESCROW_HUB
    value = 100 * 10**6
    data = b""

    attestation = generate_oms_attestation(target, value, data, risk_score=0, verdict="PASSED")

    with pytest.raises(ValueError, match="SessionInactive"):
        simulate_check_user_op_policy(
            session_config=active_session,
            target=target,
            value=value,
            data=data,
            proof_bytes=attestation["proof_bytes"]
        )


def test_oms_policy_expired_session(active_session):
    """Scenario 5: Session time window has elapsed."""
    now = int(time.time())
    active_session["expires_at"] = now - 100

    target = POLYGON_ESCROW_HUB
    value = 100 * 10**6
    data = b""

    attestation = generate_oms_attestation(target, value, data, risk_score=0, verdict="PASSED")

    with pytest.raises(ValueError, match="SessionExpired"):
        simulate_check_user_op_policy(
            session_config=active_session,
            target=target,
            value=value,
            data=data,
            proof_bytes=attestation["proof_bytes"],
            current_time=now
        )


def test_oms_policy_missing_security_attestation(active_session):
    """Scenario 6: Transaction attempted without Security Gate proof."""
    target = POLYGON_ESCROW_HUB
    value = 100 * 10**6
    data = b""

    with pytest.raises(ValueError, match="MissingSecurityAttestation"):
        simulate_check_user_op_policy(
            session_config=active_session,
            target=target,
            value=value,
            data=data,
            proof_bytes=b""
        )


def test_oms_policy_excessive_risk_rejection(active_session):
    """Scenario 7: Malicious AST code or prompt injection detected (risk_score = 90)."""
    target = POLYGON_ESCROW_HUB
    value = 100 * 10**6
    data = b"\xde\xad\xbe\xef"

    attestation = generate_oms_attestation(
        target=target,
        value=value,
        data=data,
        risk_score=90,  # CRITICAL INJECTION
        verdict="REJECTED_PROMPT_INJECTION"
    )

    with pytest.raises(ValueError, match="ExcessiveRiskScore"):
        simulate_check_user_op_policy(
            session_config=active_session,
            target=target,
            value=value,
            data=data,
            proof_bytes=attestation["proof_bytes"]
        )


def test_oms_policy_expired_attestation_replay(active_session):
    """Scenario 8: Old valid attestation replayed after expiry."""
    now = int(time.time())
    target = POLYGON_ESCROW_HUB
    value = 50 * 10**6
    data = b""

    attestation = generate_oms_attestation(
        target=target,
        value=value,
        data=data,
        risk_score=0,
        verdict="PASSED",
        validity_seconds=-10  # Already expired
    )

    with pytest.raises(ValueError, match="AttestationExpired"):
        simulate_check_user_op_policy(
            session_config=active_session,
            target=target,
            value=value,
            data=data,
            proof_bytes=attestation["proof_bytes"],
            current_time=now
        )


def test_oms_policy_forged_oracle_signature(active_session):
    """Scenario 9: Rogue key attempts to forge Security Gate attestation."""
    rogue_account = Account.create()
    target = POLYGON_ESCROW_HUB
    value = 50 * 10**6
    data = b""

    attestation = generate_oms_attestation(
        target=target,
        value=value,
        data=data,
        risk_score=0,
        verdict="PASSED",
        signer_account=rogue_account
    )

    with pytest.raises(ValueError, match="InvalidAttestationSignature"):
        simulate_check_user_op_policy(
            session_config=active_session,
            target=target,
            value=value,
            data=data,
            proof_bytes=attestation["proof_bytes"]
        )


def test_oms_policy_tampered_payload_mismatch(active_session):
    """Scenario 10: Attestation was issued for 50 USDC, but agent attempts to submit 100 USDC."""
    target = POLYGON_ESCROW_HUB
    value = 50 * 10**6
    data = b""

    attestation = generate_oms_attestation(
        target=target,
        value=value,  # Attested for 50 USDC
        data=data,
        risk_score=0,
        verdict="PASSED"
    )

    tampered_value = 100 * 10**6  # Attempting 100 USDC with 50 USDC proof

    with pytest.raises(ValueError, match="InvalidAttestationSignature"):
        simulate_check_user_op_policy(
            session_config=active_session,
            target=target,
            value=tampered_value,
            data=data,
            proof_bytes=attestation["proof_bytes"]
        )
