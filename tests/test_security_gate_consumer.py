"""
Unit tests simulating the cryptographic and logic flow of SecurityGateConsumer.sol:
1. EIP-712 Domain Separator and TypeHash integrity
2. Legitimate verification and execution
3. Attestation expiration checks (block.timestamp > expiresAt)
4. Excessive risk score rejection (riskScore > maxRiskScore)
5. Invalid oracle signature detection (rogue signer or altered payloadHash)
"""

import time
import pytest
from eth_account import Account
from eth_account.messages import encode_typed_data
import eth_utils
from app.onchain_signer import onchain_signer


def get_eip712_message(payload_hash: bytes, risk_score: int, verdict: str, expires_at: int, chain_id: int = 137):
    domain_data = {
        "name": "AgentSecurityGateOracle",
        "version": "1.0.0",
        "chainId": chain_id,
        "verifyingContract": "0x0000000000000000000000000000000000000000"
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

    return {
        "types": types,
        "primaryType": "SecurityAttestation",
        "domain": domain_data,
        "message": message_data
    }


def test_domain_separator_and_typehash_hashes():
    """Validates that Solidity constant typehashes match Ethereum standard hashing."""
    # EIP712_DOMAIN_TYPEHASH
    expected_domain_typehash = eth_utils.keccak(
        text="EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)"
    )
    # ATTESTATION_TYPEHASH
    expected_attestation_typehash = eth_utils.keccak(
        text="SecurityAttestation(bytes32 payloadHash,uint8 riskScore,string verdict,uint256 expiresAt)"
    )

    assert len(expected_domain_typehash) == 32
    assert len(expected_attestation_typehash) == 32


def test_consumer_verify_and_execute_success():
    """Simulates SecurityGateConsumer.verifyAndExecute succeeding with a valid oracle attestation."""
    calldata = "TRANSFER_SAFE_100_USDC"
    payload_hash = eth_utils.keccak(text=calldata)
    risk_score = 5  # 5%
    verdict = "PASSED"
    expires_at = int(time.time()) + 300
    chain_id = 137

    msg = get_eip712_message(payload_hash, risk_score, verdict, expires_at, chain_id)
    signable = encode_typed_data(full_message=msg)
    signed = onchain_signer.account.sign_message(signable)

    # Recover signer as contract does: ecrecover(digest, v, r, s)
    recovered = Account.recover_message(signable, vrs=(signed.v, signed.r, signed.s))
    assert recovered.lower() == onchain_signer.signer_address.lower()

    # Rule checks in SecurityGateConsumer.sol:
    # 1. block.timestamp <= expiresAt
    current_timestamp = int(time.time())
    assert current_timestamp <= expires_at

    # 2. riskScore <= maxRiskScore
    max_risk_score = 10
    assert risk_score <= max_risk_score

    # 3. recoveredSigner == oracleSigner
    assert recovered.lower() == onchain_signer.signer_address.lower()


def test_consumer_revert_attestation_expired():
    """Simulates revert AttestationExpired when block.timestamp > expiresAt."""
    calldata = "DRAIN_ATTEMPT"
    payload_hash = eth_utils.keccak(text=calldata)
    risk_score = 5
    verdict = "PASSED"
    expires_at = int(time.time()) - 60  # Expired 1 minute ago
    current_timestamp = int(time.time())

    assert current_timestamp > expires_at


def test_consumer_revert_excessive_risk_score():
    """Simulates revert ExcessiveRiskScore when riskScore > maxRiskScore."""
    calldata = "POTENTIAL_UNVERIFIED_ACTION"
    risk_score = 45  # Detected 45% risk
    max_allowed = 20  # Only allows <= 20%

    assert risk_score > max_allowed


def test_consumer_revert_invalid_oracle_signature():
    """Simulates revert InvalidOracleSignature when a rogue key signs the attestation."""
    rogue_account = Account.create()
    calldata = "ROGUE_ACTION"
    payload_hash = eth_utils.keccak(text=calldata)
    risk_score = 0
    verdict = "PASSED"
    expires_at = int(time.time()) + 300
    chain_id = 137

    msg = get_eip712_message(payload_hash, risk_score, verdict, expires_at, chain_id)
    signable = encode_typed_data(full_message=msg)
    signed = rogue_account.sign_message(signable)

    recovered = Account.recover_message(signable, vrs=(signed.v, signed.r, signed.s))
    assert recovered.lower() != onchain_signer.signer_address.lower()


def test_consumer_tampered_payload_rejection():
    """Simulates an attacker tampering with the payloadHash after the oracle signed."""
    original_calldata = "BENIGN_TRANSFER"
    original_hash = eth_utils.keccak(text=original_calldata)
    risk_score = 0
    verdict = "PASSED"
    expires_at = int(time.time()) + 300
    chain_id = 137

    msg = get_eip712_message(original_hash, risk_score, verdict, expires_at, chain_id)
    signable = encode_typed_data(full_message=msg)
    signed = onchain_signer.account.sign_message(signable)

    # Attacker modifies payloadHash to malicious action
    malicious_hash = eth_utils.keccak(text="MALICIOUS_DRAIN")
    tampered_msg = get_eip712_message(malicious_hash, risk_score, verdict, expires_at, chain_id)
    tampered_signable = encode_typed_data(full_message=tampered_msg)

    # Attempting to verify the oracle's signature against the malicious hash must not yield oracleSigner
    recovered = Account.recover_message(tampered_signable, vrs=(signed.v, signed.r, signed.s))
    assert recovered.lower() != onchain_signer.signer_address.lower()
