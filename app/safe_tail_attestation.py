"""Safe Signature Tail Appender and Safety Attestation Signer for security-gate-x402.

Produces EIP-712 cryptographic attestations matching SecurityGateVerifier.sol
and bundles them into the signature tail expected by SecurityGateSafeGuard.sol.
"""

from __future__ import annotations

import os
import time
from typing import Any, Dict, Optional, Tuple
from eth_abi import encode as abi_encode
from eth_account import Account
from eth_account.messages import encode_typed_data
from web3 import Web3


def sign_safety_attestation(
    gate_private_key: str,
    chain_id: int,
    verifying_contract: str,
    payload_hash: bytes,
    agent_wallet: str,
    target_address: str,
    max_allowed_spend: int,
    risk_score: int = 0,
    nonce: Optional[bytes] = None,
    expiry: Optional[int] = None,
) -> Dict[str, Any]:
    """Generates an EIP-712 SafetyAttestation signature for SecurityGateProtocol.sol."""
    domain_data = {
        "name": "SecurityGateX402",
        "version": "1",
        "chainId": chain_id,
        "verifyingContract": Web3.to_checksum_address(verifying_contract),
    }

    message_types = {
        "SafetyAttestation": [
            {"name": "payloadHash", "type": "bytes32"},
            {"name": "agentWallet", "type": "address"},
            {"name": "targetAddress", "type": "address"},
            {"name": "maxAllowedSpend", "type": "uint256"},
            {"name": "expiry", "type": "uint256"},
            {"name": "riskScore", "type": "uint8"},
            {"name": "nonce", "type": "bytes32"},
        ]
    }

    current_time = int(time.time())
    exp = expiry or (current_time + 60)  # 60-second default validity window
    att_nonce = nonce or os.urandom(32)

    message_data = {
        "payloadHash": payload_hash,
        "agentWallet": Web3.to_checksum_address(agent_wallet),
        "targetAddress": Web3.to_checksum_address(target_address),
        "maxAllowedSpend": max_allowed_spend,
        "expiry": exp,
        "riskScore": risk_score,
        "nonce": att_nonce,
    }

    signable = encode_typed_data(domain_data, message_types, message_data)
    signed = Account.sign_message(signable, private_key=gate_private_key)

    return {
        "attestation": message_data,
        "signature": signed.signature.hex(),
        "signature_bytes": signed.signature,
    }


def bundle_safe_signatures_with_tail(
    safe_owner_signature: bytes,
    attestation: Dict[str, Any],
    gate_signature: bytes
) -> bytes:
    """Encodes (SafetyAttestation, gateSignature) and appends it to the Safe owner signature.

    Format expected by SecurityGateSafeGuard.sol:
    [65-byte Owner Sig] + [ABI-encoded (SafetyAttestation tuple, bytes gateSignature)]
    """
    if len(safe_owner_signature) < 65:
        raise ValueError("Safe owner signature must be at least 65 bytes.")

    attestation_tuple = (
        attestation["payloadHash"],
        attestation["agentWallet"],
        attestation["targetAddress"],
        attestation["maxAllowedSpend"],
        attestation["expiry"],
        attestation["riskScore"],
        attestation["nonce"],
    )

    # Encode as tuple matching Solidity struct SafetyAttestation and bytes
    encoded_tail = abi_encode(
        ["(bytes32,address,address,uint256,uint256,uint8,bytes32)", "bytes"],
        [attestation_tuple, gate_signature]
    )

    return safe_owner_signature + encoded_tail
