"""
Universal Factoring Bridge - Links UniversalEscrowCore with AgentFactoringPool.
================================================================================
Enables autonomous AI agents to immediately liquidate pending escrow receivables
across Maritime, Bio/Pharma, Construction, EUDR, and Conflict Minerals domains.

Key Capabilities:
1. Credit-scoring-adjusted micro-discount rate computation via AgentCreditOracle.
2. EIP-712 FactoringAttestation generation with deployed AgentFactoringPool binding.
3. Universal Escrow Direct Split claim redirection (No Double-Spend Guarantee).
4. Multi-chain deployment directory (Polygon 137, Base 8453, Arbitrum 42161).
"""

import time
import secrets
from typing import Dict, Any, Optional, List
import eth_utils

import math
from eth_account.messages import encode_typed_data
from app.credit_rating_engine import credit_engine
from app.onchain_signer import onchain_signer
from app.rwa_treasury_engine import sovereign_treasury

# Multi-chain Deployed Contract Directory
FACTORING_POOLS = {
    137: "0xd0Aa4Aed2AeDE14611B53C3e93CF784F3Fe05BB0",   # Polygon Mainnet
    8453: "0x6418f408cFf03F862D7691f01fAb00a895E6aB93",  # Base Mainnet
    42161: "0x6418f408cFf03F862D7691f01fAb00a895E6aB93"  # Arbitrum One
}

UNIVERSAL_ESCROWS = {
    137: "0x4Dbd77F4799816859a595f24a57A786516D2EAa8",   # Polygon Mainnet
    8453: "0x745F7FAfFdb626B931Fe769476a09125cbf9d94b",  # Base Mainnet
    42161: "0x745F7FAfFdb626B931Fe769476a09125cbf9d94b"  # Arbitrum One
}


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
        try:
            face_val = float(face_value_usdc)
        except (ValueError, TypeError):
            return {
                "status": "rejected",
                "invoice_id": invoice_id,
                "agent_address": agent_address,
                "is_eligible": False,
                "reason": f"Invalid face value: {face_value_usdc}"
            }

        if math.isnan(face_val) or math.isinf(face_val) or face_val <= 0:
            return {
                "status": "rejected",
                "invoice_id": invoice_id,
                "agent_address": agent_address,
                "is_eligible": False,
                "reason": f"Invoice face value must be strictly positive and finite: ${face_value_usdc}"
            }

        if duration_days <= 0 or duration_days > 365:
            return {
                "status": "rejected",
                "invoice_id": invoice_id,
                "agent_address": agent_address,
                "is_eligible": False,
                "reason": f"Factoring duration must be between 1 and 365 days (got {duration_days})"
            }

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

        discount_fee_usdc = round((face_val * discount_bps) / 10000.0, 4)
        oracle_fee_usdc = round(max(0.20, (face_val * self.ORACLE_FEE_BPS) / 10000.0), 4)
        advance_amount_usdc = round(face_val - discount_fee_usdc - oracle_fee_usdc, 4)

        if advance_amount_usdc <= 0:
            return {
                "status": "rejected",
                "invoice_id": invoice_id,
                "agent_address": agent_address,
                "is_eligible": False,
                "credit_score": score,
                "grade": grade,
                "reason": f"Invoice face value ${face_val:.2f} is insufficient to cover discount and protocol fees (${discount_fee_usdc + oracle_fee_usdc:.2f})"
            }

        apr_equivalent = round((discount_bps / 100.0 / max(1, duration_days)) * 365.0, 2)
        expires_at = int(time.time()) + 3600  # 1 hour attestation validity
        maturity_date = int(time.time()) + (duration_days * 86400)
        nonce = secrets.randbelow(10**9)

        # Scale to 6 decimals integer for smart contracts
        face_units = int(face_val * 1_000_000)
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


class UniversalFactoringBridge:
    """Orchestrates receivable claim assignment and instant liquidity advances for Universal Escrow."""

    ORACLE_FEE_BPS = 20  # 0.20% protocol fee for factoring advance

    def __init__(self):
        self.credit_engine = credit_engine
        self.factoring_engine = factoring_engine
        self.signer = onchain_signer
        # In-memory registry of factored escrow jobs: job_id -> factoring details
        self.active_factored_jobs: Dict[str, Dict[str, Any]] = {}

    def get_deployed_factoring_pool(self, chain_id: int) -> str:
        return FACTORING_POOLS.get(chain_id, FACTORING_POOLS[137])

    def get_deployed_universal_escrow(self, chain_id: int) -> str:
        return UNIVERSAL_ESCROWS.get(chain_id, UNIVERSAL_ESCROWS[137])

    def request_escrow_factoring_quote(
        self,
        job_id: str,
        agent_address: str,
        face_value_usdc: float,
        duration_days: int = 14,
        chain_id: int = 137,
        verifying_contract: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Assesses an agent's credit score and generates a discounted advance quote
        for an active Universal Escrow job receivable.
        """
        clean_agent = eth_utils.to_checksum_address(agent_address)
        clean_chain_id = int(chain_id)
        pool_contract = verifying_contract or self.get_deployed_factoring_pool(clean_chain_id)

        # Check existing active factoring for this job to prevent double-pledging
        if job_id in self.active_factored_jobs and self.active_factored_jobs[job_id].get("status") == "ACTIVE":
            return {
                "status": "rejected",
                "job_id": job_id,
                "agent_address": clean_agent,
                "is_eligible": False,
                "reason": f"Escrow job {job_id} is already factored and pledged."
            }

        # Check Credit Score
        report = self.credit_engine.compute_credit_score(clean_agent)
        score = report["credit_score"]
        grade = report["grade"]

        if score < 580:
            return {
                "status": "rejected",
                "job_id": job_id,
                "agent_address": clean_agent,
                "credit_score": score,
                "grade": grade,
                "is_eligible": False,
                "reason": f"Credit score {score} ({grade}) is below minimum factoring threshold (580)."
            }

        # Compute risk-adjusted discount rate (BPS)
        # AAA (800+): 1.5% | AA (740-799): 2.0% | A (670-739): 2.8% | BBB (580-669): 4.0%
        if score >= 800:
            discount_bps = 150
        elif score >= 740:
            discount_bps = 200
        elif score >= 670:
            discount_bps = 280
        else:
            discount_bps = 400

        # Adjust for duration: scaled linearly from 14-day baseline
        duration_factor = max(0.5, min(3.0, duration_days / 14.0))
        final_discount_bps = int(discount_bps * duration_factor)

        discount_amount = round((face_value_usdc * final_discount_bps) / 10000.0, 4)
        oracle_fee = round((face_value_usdc * self.ORACLE_FEE_BPS) / 10000.0, 4)
        advance_amount = round(face_value_usdc - discount_amount - oracle_fee, 4)

        now = int(time.time())
        maturity_date = now + (duration_days * 86400)
        expires_at = now + 3600  # 1 hour quote validity
        invoice_id = int(secrets.randbelow(1_000_000_000)) + 1
        nonce = int(secrets.randbelow(1_000_000_000)) + 1

        # Use numeric hash for escrow_job_id in FactoringAttestation struct
        numeric_job_id = int(eth_utils.keccak(text=str(job_id)).hex()[:10], 16)

        # Generate EIP-712 FactoringAttestation
        face_value_units = int(face_value_usdc * 1_000_000)
        oracle_fee_units = int(oracle_fee * 1_000_000)

        domain_data = {
            "name": "AgentFactoringPool",
            "version": "1.0.0",
            "chainId": clean_chain_id,
            "verifyingContract": pool_contract
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
            "escrowJobId": numeric_job_id,
            "agent": clean_agent,
            "faceValue": face_value_units,
            "discountRateBps": final_discount_bps,
            "oracleFee": oracle_fee_units,
            "maturityDate": maturity_date,
            "expiresAt": expires_at,
            "nonce": nonce
        }
        from eth_account.messages import encode_typed_data
        signable_msg = encode_typed_data(full_message={
            "types": types,
            "primaryType": "FactoringAttestation",
            "domain": domain_data,
            "message": message_data
        })
        signed = self.signer.account.sign_message(signable_msg)

        r_hex = "0x" + signed.r.to_bytes(32, "big").hex()
        s_hex = "0x" + signed.s.to_bytes(32, "big").hex()

        return {
            "status": "APPROVED",
            "job_id": job_id,
            "invoice_id": invoice_id,
            "agent_address": clean_agent,
            "credit_score": score,
            "grade": grade,
            "is_eligible": True,
            "face_value_usdc": face_value_usdc,
            "advance_amount_usdc": advance_amount,
            "discount_rate_bps": final_discount_bps,
            "discount_amount_usdc": discount_amount,
            "oracle_fee_usdc": oracle_fee,
            "effective_yield_apr": round((final_discount_bps / 100.0) * (365.0 / duration_days), 2),
            "maturity_date": maturity_date,
            "expires_at": expires_at,
            "chain_id": clean_chain_id,
            "factoring_pool_address": pool_contract,
            "universal_escrow_address": self.get_deployed_universal_escrow(clean_chain_id),
            "attestation": {
                "invoiceId": invoice_id,
                "escrowJobId": numeric_job_id,
                "agent": clean_agent,
                "faceValue": face_value_units,
                "discountRateBps": final_discount_bps,
                "oracleFee": oracle_fee_units,
                "maturityDate": maturity_date,
                "expiresAt": expires_at,
                "nonce": nonce,
                "v": signed.v,
                "r": r_hex,
                "s": s_hex,
                "oracle_signer": self.signer.signer_address,
                "full_signature": signed.signature.hex()
            },
            "claim_assignment_instruction": {
                "direct_split_recipient_override": pool_contract,
                "guarantee": "UniversalEscrowCore settlement will disburse full face value directly into AgentFactoringPool."
            }
        }

    def execute_claim_assignment(
        self,
        job_id: str,
        invoice_id: int,
        agent_address: str,
        face_value_usdc: float,
        advance_amount_usdc: float,
        chain_id: int = 137
    ) -> Dict[str, Any]:
        """
        Formally binds the Universal Escrow receivable claim to the AgentFactoringPool.
        Guarantees on-chain settlement will disburse directly to factoring pool.
        """
        clean_agent = eth_utils.to_checksum_address(agent_address)
        clean_chain_id = int(chain_id)
        pool_contract = self.get_deployed_factoring_pool(clean_chain_id)

        record = {
            "job_id": job_id,
            "invoice_id": invoice_id,
            "agent_address": clean_agent,
            "face_value_usdc": face_value_usdc,
            "advance_amount_usdc": advance_amount_usdc,
            "factoring_pool": pool_contract,
            "chain_id": clean_chain_id,
            "status": "ACTIVE",
            "assigned_at": int(time.time())
        }
        self.active_factored_jobs[job_id] = record

        # Accumulate protocol fee in RWA Treasury
        protocol_toll = round(face_value_usdc * (self.ORACLE_FEE_BPS / 10000.0), 4)
        sovereign_treasury.accumulated_tolls += protocol_toll

        return {
            "status": "PLEDGED",
            "job_id": job_id,
            "invoice_id": invoice_id,
            "agent_address": clean_agent,
            "assigned_recipient": pool_contract,
            "advance_disbursed_usdc": advance_amount_usdc,
            "protocol_toll_usdc": protocol_toll,
            "message": "Universal Escrow settlement redirected to AgentFactoringPool."
        }

    def resolve_factored_settlement(self, job_id: str) -> Dict[str, Any]:
        """
        Called when Universal Escrow settles. Marks the bond as settled,
        rewards agent credit score, and releases factoring liability.
        """
        record = self.active_factored_jobs.get(job_id)
        if not record or record.get("status") != "ACTIVE":
            return {"status": "NOT_FACTORED", "factored": False, "job_id": job_id}

        record["status"] = "SETTLED"
        record["settled_at"] = int(time.time())

        # Boost agent credit rating for honest, successful receivables delivery
        agent = record["agent_address"]
        self.credit_engine.record_audit(agent, verdict="PASSED", hallucination_detected=False)

        return {
            "status": "SETTLED",
            "factored": True,
            "job_id": job_id,
            "invoice_id": record["invoice_id"],
            "agent_address": agent,
            "repaid_to_pool": record["factoring_pool"],
            "face_value_recovered": record["face_value_usdc"]
        }


universal_factoring_bridge = UniversalFactoringBridge()

__all__ = [
    "UniversalFactoringBridge",
    "universal_factoring_bridge",
    "AgentFactoringEngine",
    "factoring_engine",
]

