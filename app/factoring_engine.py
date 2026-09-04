"""
Autonomous AI Agent Receivables Factoring & Short-Term Bond Engine.
Calculates risk-adjusted discount rates, evaluates pending escrow milestones,
and issues cryptographic EIP-712 FactoringAttestations for AgentFactoringPool.sol.
"""

import time
import secrets
from typing import Dict, Any, Optional
from eth_account.messages import encode_typed_data
from app.credit_rating_engine import credit_engine
from app.onchain_signer import onchain_signer


class AgentFactoringEngine:
    """Evaluates agent receivables, determines discount haircut, and signs EIP-712 bond attestations."""

    ORACLE_FEE_BPS = 50  # 0.5% protocol fee

    def __init__(self):
        self.credit_engine = credit_engine
        self.signer = onchain_signer

    def get_factoring_quote(
        self,
        invoice_id: int,
        escrow_job_id: int,
        agent_address: str,
        face_value_usdc: float,
        duration_days: int = 30,
        chain_id: int = 137,
        verifying_contract: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Assesses an agent's creditworthiness to factor an escrow receivable into immediate cash.
        Issues an EIP-712 FactoringAttestation for on-chain submission.
        """
        if verifying_contract is None:
            verifying_contract = "0x0000000000000000000000000000000000000000"

        # 1. Credit Scoring Assessment
        report = self.credit_engine.compute_credit_score(agent_address)
        score = report["credit_score"]
        grade = report["grade"]

        # Low-score or malicious agents cannot factor receivables
        if score < 580:
            return {
                "status": "rejected",
                "invoice_id": invoice_id,
                "agent_address": agent_address,
                "is_eligible": False,
                "credit_score": score,
                "grade": grade,
                "reason": f"FICO Score {score} (Grade {grade}) is below minimum factoring threshold of 580."
            }

        # 2. Risk-Adjusted Discount Rates (BPS)
        if score >= 800:
            discount_bps = 200     # 2.0% for AAA Prime
        elif score >= 740:
            discount_bps = 300     # 3.0% for AA
        elif score >= 670:
            discount_bps = 450     # 4.5% for A
        else:
            discount_bps = 700     # 7.0% for B

        discount_fee_usdc = round((face_value_usdc * discount_bps) / 10000.0, 4)
        oracle_fee_usdc = round(max(0.20, (face_value_usdc * self.ORACLE_FEE_BPS) / 10000.0), 4)
        advance_amount_usdc = round(face_value_usdc - discount_fee_usdc - oracle_fee_usdc, 4)

        apr_equivalent = round((discount_bps / 100.0 / max(1, duration_days)) * 365.0, 2)
        expires_at = int(time.time()) + 3600  # 1 hour attestation validity
        maturity_date = int(time.time()) + (duration_days * 86400)
        nonce = secrets.randbelow(10**9)

        # Scale to 6 decimals integer for smart contracts
        face_units = int(face_value_usdc * 1_000_000)
        oracle_fee_units = int(oracle_fee_usdc * 1_000_000)

        # 3. Formulate EIP-712 Typed Data
        domain_data = {
            "name": "AgentFactoringPool",
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
            "FactoringAttestation": [
                {"name": "invoiceId", "type": "uint256"},
                {"name": "escrowJobId", "type": "uint256"},
                {"name": "agent", "type": "address"},
                {"name": "faceValue", "type": "uint256"},
                {"name": "discountRateBps", "type": "uint256"},
                {"name": "oracleFee", "type": "uint256"},
                {"name": "maturityDate", "type": "uint256"},
                {"name": "expiresAt", "type": "uint256"},
                {"name": "nonce", "type": "uint256"}
            ]
        }

        message_data = {
            "invoiceId": invoice_id,
            "escrowJobId": escrow_job_id,
            "agent": agent_address,
            "faceValue": face_units,
            "discountRateBps": discount_bps,
            "oracleFee": oracle_fee_units,
            "maturityDate": maturity_date,
            "expiresAt": expires_at,
            "nonce": nonce
        }

        structured_data = {
            "types": types,
            "primaryType": "FactoringAttestation",
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
            "invoice_id": invoice_id,
            "escrow_job_id": escrow_job_id,
            "agent_address": agent_address,
            "is_eligible": True,
            "credit_score": score,
            "grade": grade,
            "face_value_usdc": face_value_usdc,
            "duration_days": duration_days,
            "discount_rate_pct": discount_bps / 100.0,
            "discount_fee_usdc": discount_fee_usdc,
            "oracle_fee_usdc": oracle_fee_usdc,
            "advance_amount_usdc": advance_amount_usdc,
            "apr_equivalent_pct": apr_equivalent,
            "attestation": {
                "invoiceId": invoice_id,
                "escrowJobId": escrow_job_id,
                "agent": agent_address,
                "faceValue": face_units,
                "discountRateBps": discount_bps,
                "oracleFee": oracle_fee_units,
                "maturityDate": maturity_date,
                "expiresAt": expires_at,
                "nonce": nonce,
                "v": v,
                "r": r_hex,
                "s": s_hex,
                "oracle_signer": self.signer.signer_address,
                "chain_id": chain_id
            }
        }

    def record_settlement(self, invoice_id: int, agent_address: str, amount_settled: float) -> Dict[str, Any]:
        """
        Records full settlement of a factored bond from escrow or direct payer.
        Boosts the agent's credit score for reliable liquidity repayment.
        """
        # Reward agent with positive audit event
        self.credit_engine.record_audit(agent_address, verdict="PASSED", hallucination_detected=False)
        updated_report = self.credit_engine.compute_credit_score(agent_address)

        return {
            "status": "success",
            "invoice_id": invoice_id,
            "agent_address": agent_address,
            "amount_settled": amount_settled,
            "updated_credit_score": updated_report["credit_score"],
            "updated_grade": updated_report["grade"],
            "message": f"Invoice #{invoice_id} of ${amount_settled:.2f} USDC settled. Reputation boosted."
        }


factoring_engine = AgentFactoringEngine()
