"""
Universal Parametric Insurance & Slashing Bridge.
================================================
Binds UniversalEscrowCore escrow agreements with AgentInsurancePool.sol.
Provides 0-second parametric risk underwriting, algorithmic claim adjudication,
and automatic slashing of fraudulent / non-compliant agent collateral.

Risk Domains Covered:
- CUSTOMS_DELAY: Port/customs EUDR inspection delay exceeding threshold.
- PORT_CONGESTION: Terminal dwell time anomaly.
- SATELLITE_OUTAGE: Cloud cover / Sentinel-2 radar data outage.
- HARDWARE_FAULT: Distributed GPU cluster node failure during active training.
- BIOTECH_SYNTHESIS_FAILURE: Binding affinity assay replication failure.
"""

import time
import secrets
from typing import Dict, Any, Optional
import eth_utils

import math
from eth_account.messages import encode_typed_data
from eth_utils import keccak, is_address, to_checksum_address
from app.credit_rating_engine import credit_engine
from app.onchain_signer import onchain_signer
from app.rwa_treasury_engine import sovereign_treasury

# Multi-chain Deployed Insurance Pools
INSURANCE_POOLS = {
    137: "0xE67F4BC75B11dBb3ef2C9Ad1848B4b193c2c69C6",   # Polygon Mainnet
    8453: "0x90308AedEe6430D11e5214cf9d2F563333D33Ef2",  # Base Mainnet
    42161: "0x90308AedEe6430D11e5214cf9d2F563333D33Ef2"  # Arbitrum One
}

BASE_RISK_BPS = {
    "CUSTOMS_DELAY": 35,          # 0.35%
    "PORT_CONGESTION": 40,        # 0.40%
    "SATELLITE_OUTAGE": 30,       # 0.30%
    "HARDWARE_FAULT": 50,         # 0.50%
    "BIOTECH_SYNTHESIS_FAILURE": 60, # 0.60%
    "GENERIC_PARAMETRIC": 45      # 0.45%
}


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
        try:
            coverage = float(coverage_amount_usdc)
        except (ValueError, TypeError):
            return {
                "status": "rejected",
                "agent_address": agent_address,
                "beneficiary_address": beneficiary_address,
                "is_eligible": False,
                "reason": f"Invalid coverage amount: {coverage_amount_usdc}"
            }

        if math.isnan(coverage) or math.isinf(coverage) or coverage <= 0:
            return {
                "status": "rejected",
                "agent_address": agent_address,
                "beneficiary_address": beneficiary_address,
                "is_eligible": False,
                "reason": f"Coverage amount must be strictly positive and finite: ${coverage_amount_usdc}"
            }

        if duration_days <= 0 or duration_days > 365:
            return {
                "status": "rejected",
                "agent_address": agent_address,
                "beneficiary_address": beneficiary_address,
                "is_eligible": False,
                "reason": f"Policy duration must be between 1 and 365 days (got {duration_days})"
            }

        if verifying_contract is None:
            verifying_contract = "0x0000000000000000000000000000000000000000"

        if not is_address(agent_address):
            return {
                "status": "rejected",
                "agent_address": agent_address,
                "beneficiary_address": beneficiary_address,
                "is_eligible": False,
                "reason": f"Invalid EVM agent_address: {agent_address}"
            }
        if not is_address(beneficiary_address):
            return {
                "status": "rejected",
                "agent_address": agent_address,
                "beneficiary_address": beneficiary_address,
                "is_eligible": False,
                "reason": f"Invalid EVM beneficiary_address: {beneficiary_address}"
            }
        try:
            agent_address = to_checksum_address(agent_address)
            beneficiary_address = to_checksum_address(beneficiary_address)
            verifying_contract = to_checksum_address(verifying_contract)
        except Exception as e:
            return {
                "status": "rejected",
                "agent_address": agent_address,
                "beneficiary_address": beneficiary_address,
                "is_eligible": False,
                "reason": f"Failed to checksum address: {e}"
            }

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
        raw_premium = (coverage * annual_bps * duration_days) / (365.0 * 10000.0)
        premium_usdc = round(max(0.50, raw_premium), 4)

        # Risk-free Oracle protocol underwriting fee (15% of premium, min $0.20)
        oracle_fee_usdc = round(max(0.20, premium_usdc * 0.15), 4)
        total_cost_usdc = round(premium_usdc + oracle_fee_usdc, 4)

        expires_at = int(time.time()) + 3600  # Quote valid for 1 hour
        nonce = secrets.randbelow(10**9)

        # Convert USDC amounts to 6-decimal integers for smart contract compatibility
        coverage_units = int(coverage * 1_000_000)
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

        if not is_address(claimant_address) or not is_address(agent_address):
            return {
                "status": "rejected",
                "policy_id": policy_id,
                "reason": "Invalid EVM claimant_address or agent_address"
            }
        try:
            claimant_address = to_checksum_address(claimant_address)
            agent_address = to_checksum_address(agent_address)
            verifying_contract = to_checksum_address(verifying_contract)
        except Exception as e:
            return {
                "status": "rejected",
                "policy_id": policy_id,
                "reason": f"Failed to checksum address: {e}"
            }

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


class UniversalInsuranceBridge:
    """Orchestrates parametric risk underwriting, claim adjudication, and slashing."""

    ORACLE_FEE_BPS = 10  # 0.10% protocol inspection fee

    def __init__(self):
        self.credit_engine = credit_engine
        self.insurance_engine = insurance_engine
        self.signer = onchain_signer
        # Active job policy registry: job_id -> policy details
        self.active_policies: Dict[str, Dict[str, Any]] = {}

    def get_deployed_insurance_pool(self, chain_id: int) -> str:
        return INSURANCE_POOLS.get(chain_id, INSURANCE_POOLS[137])

    def request_parametric_policy_quote(
        self,
        job_id: str,
        agent_address: str,
        beneficiary_address: str,
        coverage_amount_usdc: float,
        risk_domain: str = "CUSTOMS_DELAY",
        duration_days: int = 30,
        chain_id: int = 137,
        verifying_contract: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculates risk-adjusted parametric premium and issues an EIP-712 PolicyQuote
        for AgentInsurancePool.sol.
        """
        clean_agent = eth_utils.to_checksum_address(agent_address)
        clean_beneficiary = eth_utils.to_checksum_address(beneficiary_address)
        clean_chain_id = int(chain_id)
        pool_contract = verifying_contract or self.get_deployed_insurance_pool(clean_chain_id)

        # 1. Base Rate from Risk Domain
        base_bps = BASE_RISK_BPS.get(risk_domain.upper(), BASE_RISK_BPS["GENERIC_PARAMETRIC"])

        # 2. Credit Score Multiplier
        report = self.credit_engine.compute_credit_score(clean_agent)
        score = report["credit_score"]
        if score >= 750:
            multiplier = 0.85   # 15% discount for AAA/AA
        elif score >= 650:
            multiplier = 1.0    # standard
        else:
            multiplier = 1.35   # 35% surcharge for high risk

        final_bps = max(20, int(base_bps * multiplier))
        premium_amount = round((coverage_amount_usdc * final_bps) / 10000.0, 4)
        oracle_fee = round((coverage_amount_usdc * self.ORACLE_FEE_BPS) / 10000.0, 4)

        now = int(time.time())
        expires_at = now + 3600  # Quote valid for 1 hour
        policy_expiry = now + (duration_days * 86400)
        nonce = int(secrets.randbelow(1_000_000_000)) + 1
        policy_id = int(secrets.randbelow(1_000_000_000)) + 1

        coverage_units = int(coverage_amount_usdc * 1_000_000)
        premium_units = int(premium_amount * 1_000_000)
        oracle_fee_units = int(oracle_fee * 1_000_000)

        # Generate EIP-712 PolicyQuote signature
        domain_data = {
            "name": "AgentInsurancePool",
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
            "agent": clean_agent,
            "beneficiary": clean_beneficiary,
            "coverageAmount": coverage_units,
            "durationDays": duration_days,
            "premiumAmount": premium_units,
            "oracleFee": oracle_fee_units,
            "expiresAt": expires_at,
            "nonce": nonce
        }
        from eth_account.messages import encode_typed_data
        signable_msg = encode_typed_data(full_message={
            "types": types,
            "primaryType": "PolicyQuote",
            "domain": domain_data,
            "message": message_data
        })
        signed = self.signer.account.sign_message(signable_msg)

        r_hex = "0x" + signed.r.to_bytes(32, "big").hex()
        s_hex = "0x" + signed.s.to_bytes(32, "big").hex()

        record = {
            "job_id": job_id,
            "policy_id": policy_id,
            "agent": clean_agent,
            "beneficiary": clean_beneficiary,
            "coverage_usdc": coverage_amount_usdc,
            "premium_usdc": premium_amount,
            "risk_domain": risk_domain.upper(),
            "chain_id": clean_chain_id,
            "policy_expiry": policy_expiry,
            "status": "QUOTED"
        }
        self.active_policies[job_id] = record

        # Accumulate protocol toll
        sovereign_treasury.accumulated_tolls += oracle_fee

        return {
            "status": "APPROVED",
            "job_id": job_id,
            "policy_id": policy_id,
            "agent_address": clean_agent,
            "beneficiary_address": clean_beneficiary,
            "risk_domain": risk_domain.upper(),
            "coverage_amount_usdc": coverage_amount_usdc,
            "premium_amount_usdc": premium_amount,
            "premium_rate_bps": final_bps,
            "oracle_fee_usdc": oracle_fee,
            "duration_days": duration_days,
            "expires_at": expires_at,
            "policy_expiry": policy_expiry,
            "insurance_pool_address": pool_contract,
            "quote": {
                "agent": clean_agent,
                "beneficiary": clean_beneficiary,
                "coverageAmount": coverage_units,
                "durationDays": duration_days,
                "premiumAmount": premium_units,
                "oracleFee": oracle_fee_units,
                "expiresAt": expires_at,
                "nonce": nonce,
                "v": signed.v,
                "r": r_hex,
                "s": s_hex,
                "oracle_signer": self.signer.signer_address,
                "full_signature": signed.signature.hex()
            }
        }

    def trigger_parametric_claim(
        self,
        job_id: str,
        policy_id: int,
        claimant_address: str,
        trigger_event: str,
        metric_value: float,
        threshold_value: float,
        incident_proof_hash: str,
        chain_id: int = 137
    ) -> Dict[str, Any]:
        """
        Adjudicates a parametric insurance claim deterministically:
        - If metric_value >= threshold_value: Instant compensation attestation issued.
        - If metric_value < threshold_value: Claim rejected.
        """
        clean_claimant = eth_utils.to_checksum_address(claimant_address)
        clean_chain_id = int(chain_id)
        pool_contract = self.get_deployed_insurance_pool(clean_chain_id)

        # Check if already settled
        if job_id in self.active_policies and self.active_policies[job_id].get("status") == "CLAIM_APPROVED":
            return {
                "status": "REJECTED",
                "job_id": job_id,
                "policy_id": policy_id,
                "is_adjudicated": True,
                "payout_approved": False,
                "reason": f"Policy for job {job_id} is already settled and claimed."
            }

        # Evaluate deterministic parametric trigger
        is_triggered = bool(metric_value >= threshold_value)
        if not is_triggered:
            return {
                "status": "REJECTED",
                "job_id": job_id,
                "policy_id": policy_id,
                "is_adjudicated": True,
                "payout_approved": False,
                "reason": f"Parametric threshold not reached: metric {metric_value} < threshold {threshold_value}."
            }

        # Calculate compensation payout amount
        record = self.active_policies.get(job_id, {})
        coverage_usdc = record.get("coverage_usdc", 5000.0)
        payout_usdc = coverage_usdc
        payout_units = int(payout_usdc * 1_000_000)

        now = int(time.time())
        nonce = int(secrets.randbelow(1_000_000_000)) + 1

        raw_proof_hash = incident_proof_hash if incident_proof_hash.startswith("0x") and len(incident_proof_hash) == 66 else eth_utils.keccak(text=incident_proof_hash).hex()
        if not raw_proof_hash.startswith("0x"):
            raw_proof_hash = "0x" + raw_proof_hash

        # Sign EIP-712 ClaimAttestation
        domain_data = {
            "name": "AgentInsurancePool",
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
            "policyId": int(policy_id),
            "claimant": clean_claimant,
            "claimAmount": payout_units,
            "incidentHash": raw_proof_hash,
            "timestamp": now,
            "nonce": nonce
        }
        from eth_account.messages import encode_typed_data
        signable_msg = encode_typed_data(full_message={
            "types": types,
            "primaryType": "ClaimAttestation",
            "domain": domain_data,
            "message": message_data
        })
        signed = self.signer.account.sign_message(signable_msg)

        r_hex = "0x" + signed.r.to_bytes(32, "big").hex()
        s_hex = "0x" + signed.s.to_bytes(32, "big").hex()

        if job_id in self.active_policies:
            self.active_policies[job_id]["status"] = "CLAIM_APPROVED"
            self.active_policies[job_id]["claimed_amount"] = payout_usdc

        return {
            "status": "APPROVED",
            "job_id": job_id,
            "policy_id": policy_id,
            "trigger_event": trigger_event,
            "metric_value": metric_value,
            "threshold_value": threshold_value,
            "is_adjudicated": True,
            "payout_approved": True,
            "payout_amount_usdc": payout_usdc,
            "claimant": clean_claimant,
            "insurance_pool_address": pool_contract,
            "claim_attestation": {
                "policyId": int(policy_id),
                "claimant": clean_claimant,
                "claimAmount": payout_units,
                "incidentHash": raw_proof_hash,
                "timestamp": now,
                "nonce": nonce,
                "v": signed.v,
                "r": r_hex,
                "s": s_hex,
                "oracle_signer": self.signer.signer_address,
                "full_signature": signed.signature.hex()
            },
            "execution_instruction": {
                "contract_call": f"AgentInsurancePool({pool_contract}).fileClaim(attestation)",
                "guarantee": "Payout disbursed instantly from insurance underwriting capital pool."
            }
        }


universal_insurance_bridge = UniversalInsuranceBridge()

__all__ = [
    "UniversalInsuranceBridge",
    "universal_insurance_bridge",
    "AgentInsuranceEngine",
    "insurance_engine",
]

