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

from app.credit_rating_engine import credit_engine
from app.insurance_engine import insurance_engine
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
