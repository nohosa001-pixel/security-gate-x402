"""
Autonomous Agent Escrow Oracle Engine.
Provides deterministic NLI hallucination & security audits for agent task deliverables,
issuing EIP-712 cryptographic attestations for AgentEscrow.sol on Polygon & EVM chains.
"""

import time
from typing import Dict, Any, Optional
import eth_utils
from eth_account import Account
from eth_account.messages import encode_typed_data

from app.security_engine import audit_payload
from app.onchain_signer import onchain_signer


class AgentEscrowEngine:
    """Evaluates task deliverables and issues cryptographic EIP-712 escrow attestations."""

    def __init__(self):
        self.signer = onchain_signer

    def evaluate_deliverable(
        self,
        job_id: int,
        deliverable: str,
        ground_truth_spec: Optional[str] = None,
        is_code: bool = False,
        chain_id: int = 137,
        verifying_contract: str = "0x0000000000000000000000000000000000000000",
        validity_seconds: int = 600
    ) -> Dict[str, Any]:
        """
        Audits deliverable text/code against requirements and signs an EscrowAttestation.
        """
        # 1. Deterministic Security & NLI Factuality Audit
        audit = audit_payload(
            text=deliverable,
            is_code=is_code,
            ground_truth=ground_truth_spec
        )

        deliverable_hash = eth_utils.keccak(text=deliverable)
        deliverable_hash_hex = "0x" + deliverable_hash.hex()

        now = int(time.time())
        expires_at = now + validity_seconds
        risk_score_int = int(round(audit.risk_score * 100))  # Convert 0.0-1.0 float to 0-100 uint8

        # 2. EIP-712 Typed Data Encoding matching AgentEscrow.sol
        domain_data = {
            "name": "AgentEscrowOracle",
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
            "EscrowAttestation": [
                {"name": "jobId", "type": "uint256"},
                {"name": "deliverableHash", "type": "bytes32"},
                {"name": "riskScore", "type": "uint8"},
                {"name": "verdict", "type": "string"},
                {"name": "expiresAt", "type": "uint256"}
            ]
        }

        message_data = {
            "jobId": job_id,
            "deliverableHash": deliverable_hash,
            "riskScore": risk_score_int,
            "verdict": audit.verdict,
            "expiresAt": expires_at
        }

        structured_data = {
            "types": types,
            "primaryType": "EscrowAttestation",
            "domain": domain_data,
            "message": message_data
        }

        signable_message = encode_typed_data(full_message=structured_data)
        signed = self.signer.account.sign_message(signable_message)

        v = signed.v
        r_hex = "0x" + signed.r.to_bytes(32, "big").hex()
        s_hex = "0x" + signed.s.to_bytes(32, "big").hex()

        return {
            "status": "success",
            "job_id": job_id,
            "verdict": audit.verdict,
            "is_safe": audit.is_safe,
            "risk_score": audit.risk_score,
            "threats": audit.threats,
            "deliverable_hash": deliverable_hash_hex,
            "attestation": {
                "jobId": job_id,
                "deliverableHash": deliverable_hash_hex,
                "riskScore": risk_score_int,
                "verdict": audit.verdict,
                "expiresAt": expires_at,
                "v": v,
                "r": r_hex,
                "s": s_hex,
                "oracle_signer": self.signer.signer_address,
                "chain_id": chain_id
            }
        }


escrow_engine = AgentEscrowEngine()
