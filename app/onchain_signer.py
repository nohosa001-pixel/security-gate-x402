"""
On-Chain Cryptographic Signer & Calldata Generator for Agent Security Gate x402.
Produces EIP-712 typed structured data signatures and raw Solidity ABI calldata (v, r, s)
for smart contract-level autonomous agent guardrails.
"""

import os
import time
from typing import Dict, Any
from eth_account import Account
from eth_account.messages import encode_typed_data
import eth_utils
import eth_abi


class OnchainSecuritySigner:
    """Signs security audit payloads using EIP-712 for EVM smart contracts."""

    INSECURE_TEST_KEY = "0x4f3edf983ac636a65a842ce7c78d9aa706d3b113bce9c46f30d7d21715b23b1d"

    def __init__(self):
        # Determine environment: Cloud Run sets K_SERVICE, production flag via APP_ENV / NODE_ENV / ENV
        is_production = bool(
            os.getenv("K_SERVICE")
            or os.getenv("APP_ENV", "").lower() in ("prod", "production")
            or os.getenv("ENV", "").lower() in ("prod", "production")
        )

        # Master private key for gate oracle signer
        raw_key = os.getenv("GATE_PRIVATE_KEY") or os.getenv("DEPLOYER_PRIVATE_KEY") or os.getenv("SERVER_PRIVATE_KEY")

        if raw_key:
            raw_key = raw_key.strip().strip('"').strip("'")
            if not raw_key.startswith("0x"):
                raw_key = "0x" + raw_key
            self.private_key = raw_key
        else:
            if is_production:
                raise RuntimeError(
                    "🚨 [CRITICAL SECURITY ERROR] Production environment detected (Cloud Run/prod), "
                    "but no valid GATE_PRIVATE_KEY / DEPLOYER_PRIVATE_KEY / SERVER_PRIVATE_KEY was supplied! "
                    "Refusing to boot with default insecure test key to prevent unauthorized attestation forgery."
                )
            self.private_key = self.INSECURE_TEST_KEY

        # Validate that production is not accidentally using the publicly known insecure test key
        if is_production and self.private_key.lower() == self.INSECURE_TEST_KEY.lower():
            raise RuntimeError(
                "🚨 [CRITICAL SECURITY ERROR] Production environment cannot use the publicly known test private key! "
                "Configure a secure private key via Secret Manager or GATE_PRIVATE_KEY."
            )

        try:
            self.account = Account.from_key(self.private_key)
            self.signer_address = self.account.address
        except Exception as e:
            if is_production:
                raise RuntimeError(f"🚨 [CRITICAL SECURITY ERROR] Failed to load private key in production: {e}")
            # Fallback to deterministic default testing signer in non-production only
            self.private_key = self.INSECURE_TEST_KEY
            self.account = Account.from_key(self.private_key)
            self.signer_address = self.account.address

    def generate_eip712_signature(
        self,
        action_payload: str,
        risk_score: float,
        verdict: str,
        chain_id: int = 137,
        validity_seconds: int = 300,
        verifying_contract: str = "0x0000000000000000000000000000000000000000"
    ) -> Dict[str, Any]:
        """
        Signs an EIP-712 SecurityAttestation struct and formats v, r, s calldata.
        """
        # Calculate keccak256 hash of action payload
        payload_hash = eth_utils.keccak(text=action_payload)
        payload_hash_hex = "0x" + payload_hash.hex()

        now = int(time.time())
        expires_at = now + validity_seconds
        # Safely normalize risk score to integer 0-100 basis (uint8 range [0, 100])
        if risk_score <= 1.0:
            risk_score_int = int(round(risk_score * 100))
        else:
            risk_score_int = int(round(risk_score))
        risk_score_int = min(max(risk_score_int, 0), 100)

        domain_data = {
            "name": "AgentSecurityGateOracle",
            "version": "1.0.0",
            "chainId": chain_id,
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
            "riskScore": risk_score_int,
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
        signed = self.account.sign_message(signable_msg)

        r_hex = "0x" + signed.r.to_bytes(32, byteorder="big").hex()
        s_hex = "0x" + signed.s.to_bytes(32, byteorder="big").hex()
        v = signed.v

        # Encode raw Solidity calldata using eth_abi
        try:
            abi_types = ["bytes32", "uint8", "uint256", "uint8", "bytes32", "bytes32"]
            abi_values = [payload_hash, risk_score_int, expires_at, v, signed.r.to_bytes(32, "big"), signed.s.to_bytes(32, "big")]
            raw_calldata = "0x" + eth_abi.encode(abi_types, abi_values).hex()
        except Exception:
            raw_calldata = f"{payload_hash_hex}{risk_score_int:02x}{expires_at:064x}{v:02x}{r_hex[2:]}{s_hex[2:]}"

        return {
            "status": "success",
            "action_payload_hash": payload_hash_hex,
            "risk_score": risk_score,
            "verdict": verdict,
            "is_safe": verdict == "PASSED",
            "chain_id": chain_id,
            "signer_address": self.signer_address,
            "signer": self.signer_address,
            "v": v,
            "r": r_hex,
            "s": s_hex,
            "abi_calldata": raw_calldata,
            "expires_at": expires_at
        }


onchain_signer = OnchainSecuritySigner()
ORACLE_ACCOUNT = onchain_signer.account


def generate_eip712_attestation(
    agent_output: str,
    risk_score: float,
    verdict: str,
    chain_id: int = 137,
    validity_seconds: int = 300,
    verifying_contract: str = "0x0000000000000000000000000000000000000000"
) -> Dict[str, Any]:
    """Generates an EIP-712 security attestation dict using the active signer."""
    sig_res = onchain_signer.generate_eip712_signature(
        action_payload=agent_output,
        risk_score=risk_score,
        verdict=verdict,
        chain_id=chain_id,
        validity_seconds=validity_seconds,
        verifying_contract=verifying_contract
    )
    return {
        "status": "attested",
        "payload_hash": sig_res["action_payload_hash"],
        "risk_score": int(round(risk_score * 100)) if risk_score <= 1.0 else int(round(risk_score)),
        "verdict": verdict,
        "expires_at": sig_res["expires_at"],
        "chain_id": chain_id,
        "oracle_signer": sig_res["signer_address"],
        "signer": sig_res["signer_address"],
        "signer_address": sig_res["signer_address"],
        "v": sig_res["v"],
        "r": sig_res["r"],
        "s": sig_res["s"],
        "signature": f"{sig_res['r']}{sig_res['s'][2:]}{sig_res['v']:02x}",
        "abi_calldata": sig_res["abi_calldata"]
    }


def verify_attestation_signature(
    attestation: Dict[str, Any],
    chain_id: int = 137,
    verifying_contract: str = "0x0000000000000000000000000000000000000000"
) -> bool:
    """Verifies that an attestation was signed by the valid Oracle account."""
    try:
        domain_data = {
            "name": "AgentSecurityGateOracle",
            "version": "1.0.0",
            "chainId": chain_id,
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
        payload_hex = attestation.get("payload_hash") or attestation.get("action_payload_hash")
        if payload_hex.startswith("0x"):
            payload_hex = payload_hex[2:]
            
        raw_risk = attestation["risk_score"]
        # If risk_score was given as float 0.0-1.0, convert to basis points 0-100
        if isinstance(raw_risk, float) and raw_risk <= 1.0:
            risk_score_int = int(round(raw_risk * 100))
        else:
            risk_score_int = int(raw_risk)

        message_data = {
            "payloadHash": bytes.fromhex(payload_hex),
            "riskScore": risk_score_int,
            "verdict": attestation["verdict"],
            "expiresAt": int(attestation["expires_at"])
        }
        structured_data = {
            "types": types,
            "primaryType": "SecurityAttestation",
            "domain": domain_data,
            "message": message_data
        }
        signable_msg = encode_typed_data(full_message=structured_data)
        
        # Reconstruct signature bytes (r: 32, s: 32, v: 1)
        r_bytes = bytes.fromhex(attestation["r"][2:])
        s_bytes = bytes.fromhex(attestation["s"][2:])
        v_byte = bytes([attestation["v"]])
        sig_bytes = r_bytes + s_bytes + v_byte

        recovered_address = Account.recover_message(signable_msg, signature=sig_bytes)
        return recovered_address.lower() == onchain_signer.signer_address.lower()
    except Exception:
        return False

