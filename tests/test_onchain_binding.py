"""
On-chain EIP-712 Binding Tests: Cryptographic attestation, calldata generation, and signature integrity.
"""

import pytest
from eth_account import Account
from eth_account.messages import encode_typed_data
from app.onchain_signer import onchain_signer


def test_onchain_eip712_signer():
    payload = "TRANSFER_ACTION: 1000 USDC"
    res = onchain_signer.generate_eip712_signature(
        action_payload=payload,
        risk_score=0.05,
        verdict="PASSED",
        chain_id=137
    )

    assert res["status"] == "success"
    assert res["signer_address"] == onchain_signer.signer_address
    assert res["v"] in [27, 28]
    assert res["r"].startswith("0x") and len(res["r"]) == 66
    assert res["s"].startswith("0x") and len(res["s"]) == 66
    assert res["abi_calldata"].startswith("0x")
    assert res["action_payload_hash"].startswith("0x")


def test_onchain_signature_recovery():
    payload = "CALL_SWAP_ROUTER: 0x1111111254EEB25477B68fb85Ed929f73A960582"
    res = onchain_signer.generate_eip712_signature(
        action_payload=payload,
        risk_score=0.0,
        verdict="PASSED",
        chain_id=137
    )

    domain_data = {
        "name": "AgentSecurityGateOracle",
        "version": "1.0.0",
        "chainId": 137,
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
        "payloadHash": bytes.fromhex(res["action_payload_hash"][2:]),
        "riskScore": int(round(res["risk_score"] * 100)),
        "verdict": res["verdict"],
        "expiresAt": res["expires_at"]
    }

    structured_data = {
        "types": types,
        "primaryType": "SecurityAttestation",
        "domain": domain_data,
        "message": message_data
    }

    signable_msg = encode_typed_data(full_message=structured_data)
    recovered = Account.recover_message(signable_msg, vrs=(res["v"], int(res["r"], 16), int(res["s"], 16)))
    assert recovered.lower() == onchain_signer.signer_address.lower()
