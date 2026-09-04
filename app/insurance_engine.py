"""
Autonomous AI Agent Malpractice / Failure Insurance Engine.
Calculates actuarial underwriting quotes, manages risk factors from credit history,
and provides cryptographic EIP-712 claim adjudication attestations for AgentInsurancePool.sol.
"""

import time
import secrets
from typing import Dict, Any, Optional
from eth_account.messages import encode_typed_data
from eth_utils import keccak
from app.credit_rating_engine import credit_engine
from app.onchain_signer import onchain_signer


class AgentInsuranceEngine:
    """Actuarial underwriting engine and instant claim adjudicator for autonomous agents."""

    def __init__(self):
        self.credit_engine = credit_engine
        self.signer = onchain_signer

    def get_policy_quote(
        self,
        agent_address: str,
        beneficiary_address: str,
        coverage_amount_usdc: float,
        duration_days: int = 30,
        chain_id: int = 137,
        verifying_contract: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculates actuarial premium and issues an EIP-712 PolicyQuote for AgentInsurancePool.sol.
        """
        if verifying_contract is None:
            verifying_contract = "0x0000000000000000000000000000000000000000"

        # 1. Evaluate Credit & Risk Profile
        report = self.credit_engine.compute_credit_score(agent_address)
        score = report["credit_score"]
        grade = report["grade"]

        # 2. Actuarial Premium Rates based on FICO Risk Grade
        if score >= 800:
            annual_bps = 150      # 1.5% APY for AAA
        elif score >= 740:
            annual_bps = 250      # 2.5% APY for AA
        elif score >= 670:
            annual_bps = 400      # 4.0% APY for A
        elif score >= 580:
            annual_bps = 650      # 6.5% APY for B
        else:
            annual_bps = 1000     # 10.0% APY for C/D

        # Premium calculation: coverage * rate * (duration / 365)
        raw_premium = (coverage_amount_usdc * annual_bps * duration_days) / (365.0 * 10000.0)
        premium_usdc = round(max(0.50, raw_premium), 4)

        # Risk-free Oracle protocol underwriting fee (15% of premium, min $0.20)
        oracle_fee_usdc = round(max(0.20, premium_usdc * 0.15), 4)
        total_cost_usdc = round(premium_usdc + oracle_fee_usdc, 4)

        expires_at = int(time.time()) + 3600  # Quote valid for 1 hour
        nonce = secrets.randbelow(10**9)

        # Convert USDC amounts to 6-decimal integers for smart contract compatibility
        coverage_units = int(coverage_amount_usdc * 1_000_000)
        premium_units = int(premium_usdc * 1_000_000)
        fee_units = int(oracle_fee_usdc * 1_000_000)

        # 3. Formulate EIP-712 Typed Data
        domain_data = {
            "name": "AgentInsurancePool",
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
            "PolicyQuote": [
                {"name": "agent", "type": "address"},
                {"name": "beneficiary", "type": "address"},
                {"name": "coverageAmount", "type": "uint256"},
                {"name": "durationDays", "type": "uint256"},
                {"name": "premiumAmount", "type": "uint256"},
                {"name": "oracleFee", "type": "uint256"},
                {"name": "expiresAt", "type": "uint256"},
                {"name": "nonce", "type": "uint256"}
            ]
        }

        message_data = {
            "agent": agent_address,
            "beneficiary": beneficiary_address,
            "coverageAmount": coverage_units,
            "durationDays": duration_days,
            "premiumAmount": premium_units,
            "oracleFee": fee_units,
            "expiresAt": expires_at,
            "nonce": nonce
        }

        structured_data = {
            "types": types,
            "primaryType": "PolicyQuote",
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
            "agent_address": agent_address,
            "beneficiary_address": beneficiary_address,
            "credit_score": score,
            "grade": grade,
            "coverage_amount_usdc": coverage_amount_usdc,
            "duration_days": duration_days,
            "annual_premium_rate_pct": annual_bps / 100.0,
            "premium_amount_usdc": premium_usdc,
            "oracle_fee_usdc": oracle_fee_usdc,
            "total_cost_usdc": total_cost_usdc,
            "expires_at": expires_at,
            "attestation": {
                "agent": agent_address,
                "beneficiary": beneficiary_address,
                "coverageAmount": coverage_units,
                "durationDays": duration_days,
                "premiumAmount": premium_units,
                "oracleFee": fee_units,
                "expiresAt": expires_at,
                "nonce": nonce,
                "v": v,
                "r": r_hex,
                "s": s_hex,
                "oracle_signer": self.signer.signer_address,
                "chain_id": chain_id
            }
        }

    def adjudicate_claim(
        self,
        policy_id: int,
        agent_address: str,
        claimant_address: str,
        claim_amount_usdc: float,
        incident_description: str,
        chain_id: int = 137,
        verifying_contract: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Adjudicates an AI failure or malicious exploit claim, producing a cryptographic EIP-712
        ClaimAttestation to disburse compensation from AgentInsurancePool.sol.
        Also penalizes the responsible agent's credit score.
        """
        if verifying_contract is None:
            verifying_contract = "0x0000000000000000000000000000000000000000"

        incident_hash = keccak(text=f"INCIDENT:{policy_id}:{agent_address}:{incident_description}")
        incident_hash_hex = "0x" + incident_hash.hex()
        timestamp = int(time.time())
        nonce = secrets.randbelow(10**9)
        claim_units = int(claim_amount_usdc * 1_000_000)

        domain_data = {
            "name": "AgentInsurancePool",
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
            "ClaimAttestation": [
                {"name": "policyId", "type": "uint256"},
                {"name": "claimant", "type": "address"},
                {"name": "claimAmount", "type": "uint256"},
                {"name": "incidentHash", "type": "bytes32"},
                {"name": "timestamp", "type": "uint256"},
                {"name": "nonce", "type": "uint256"}
            ]
        }

        message_data = {
            "policyId": policy_id,
            "claimant": claimant_address,
            "claimAmount": claim_units,
            "incidentHash": incident_hash,
            "timestamp": timestamp,
            "nonce": nonce
        }

        structured_data = {
            "types": types,
            "primaryType": "ClaimAttestation",
            "domain": domain_data,
            "message": message_data
        }

        signable_message = encode_typed_data(full_message=structured_data)
        signed = self.signer.account.sign_message(signable_message)

        v = signed.v
        r_hex = "0x" + signed.r.to_bytes(32, "big").hex()
        s_hex = "0x" + signed.s.to_bytes(32, "big").hex()

        # Enforce on-chain credit penalty on faulty agent
        for _ in range(3):
            self.credit_engine.record_audit(
                agent_address=agent_address,
                verdict="BLOCKED",
                hallucination_detected=True
            )
        updated_report = self.credit_engine.compute_credit_score(agent_address)

        return {
            "status": "success",
            "policy_id": policy_id,
            "claimant": claimant_address,
            "claim_amount_usdc": claim_amount_usdc,
            "incident_hash": incident_hash_hex,
            "faulty_agent": agent_address,
            "agent_updated_credit_score": updated_report["credit_score"],
            "agent_updated_grade": updated_report["grade"],
            "attestation": {
                "policyId": policy_id,
                "claimant": claimant_address,
                "claimAmount": claim_units,
                "incidentHash": incident_hash_hex,
                "timestamp": timestamp,
                "nonce": nonce,
                "v": v,
                "r": r_hex,
                "s": s_hex,
                "oracle_signer": self.signer.signer_address,
                "chain_id": chain_id
            }
        }


insurance_engine = AgentInsuranceEngine()
