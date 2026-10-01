"""
MineralsTruthAdapter - Responsible & Conflict-Free Minerals Truth Verification Engine.
======================================================================================
Validates real-world supply chain minerals provenance:
1. 3TG & Battery Critical Minerals: Tin, Tantalum, Tungsten, Gold, Cobalt, Lithium, Nickel.
2. Smelter / Refiner Compliance: RMI (Responsible Minerals Initiative) audited smelter ID & conformant status.
3. Chain-of-Custody (CoC): Verified bag-and-tag / mass-balance upstream trace.
4. Human Rights & Child Labor Zero-Tolerance: OECD Annex II risk mitigation confirmed.

Issues EIP-712 MineralsTruthAttestation for UniversalEscrowCore.sol.
"""

import time
from typing import Dict, Any, List, Optional
import eth_utils
from eth_account import Account
from eth_account.messages import encode_typed_data

from app.onchain_signer import onchain_signer

SUPPORTED_MINERAL_TYPES = {
    "tin", "tantalum", "tungsten", "gold", "3tg", "cobalt", "lithium", "nickel", "copper"
}

VALID_SMELTER_STATUSES = {"CONFORMANT", "ACTIVE", "CERTIFIED"}


class MineralsTruthAdapter:
    """Evaluates conflict-free mineral provenance and signs cryptographic proof."""

    DOMAIN_INT = 4  # CONFLICT_MINERALS

    def __init__(self, signer=None):
        self.signer = signer or onchain_signer

    def verify_minerals_truth(
        self,
        job_id: str,
        mineral_type: str,
        smelter_id: str,
        smelter_audit_status: str,
        mine_country_code: str,
        chain_of_custody_verified: bool,
        child_labor_free: bool,
        conflict_region: bool = False,
        enhanced_due_diligence: bool = True,
        chain_id: int = 137,
        verifying_contract: str = "0x5555555555555555555555555555555555555555",
        validity_seconds: int = 3600
    ) -> Dict[str, Any]:
        """
        Validates Minerals criteria:
        - mineral_type is recognized (3TG + critical minerals)
        - smelter_id valid and smelter_audit_status is CONFORMANT/ACTIVE
        - chain_of_custody_verified is True
        - child_labor_free is True (zero tolerance)
        - if conflict_region is True, enhanced_due_diligence must be True
        """
        # 1. Mineral Type Check
        clean_mineral = mineral_type.strip().lower()
        mineral_valid = clean_mineral in SUPPORTED_MINERAL_TYPES

        # 2. Smelter Audit Status Check
        clean_smelter_status = smelter_audit_status.strip().upper()
        smelter_valid = bool(smelter_id and len(smelter_id.strip()) >= 4) and (clean_smelter_status in VALID_SMELTER_STATUSES)

        # 3. Chain of Custody & Human Rights
        coc_valid = bool(chain_of_custody_verified)
        human_rights_valid = bool(child_labor_free)

        # 4. Conflict Region Enhanced Due Diligence
        if conflict_region:
            conflict_risk_passed = bool(enhanced_due_diligence)
        else:
            conflict_risk_passed = True

        is_valid = (
            mineral_valid
            and smelter_valid
            and coc_valid
            and human_rights_valid
            and conflict_risk_passed
        )

        # Formulate canonical truth digest
        truth_material = (
            f"MINERALS:{job_id}:{clean_mineral}:{smelter_id.strip().upper()}:"
            f"{clean_smelter_status}:{mine_country_code.strip().upper()}:"
            f"{int(coc_valid)}:{int(human_rights_valid)}:{int(conflict_risk_passed)}"
        )
        truth_hash = eth_utils.keccak(text=truth_material)
        truth_hash_hex = "0x" + truth_hash.hex()

        now = int(time.time())
        expires_at = now + validity_seconds

        # Format job_id bytes32
        job_id_bytes32 = eth_utils.to_hex(eth_utils.to_bytes(text=job_id).ljust(32, b"\0")) if len(job_id) <= 32 else job_id

        # Sign EIP-712 MineralsTruthAttestation
        domain_data = {
            "name": "MineralsTruthAdapter",
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
            "MineralsTruthAttestation": [
                {"name": "jobId", "type": "bytes32"},
                {"name": "truthHash", "type": "bytes32"},
                {"name": "mineralType", "type": "string"},
                {"name": "smelterId", "type": "string"},
                {"name": "conflictFree", "type": "bool"},
                {"name": "isValid", "type": "bool"},
                {"name": "expiresAt", "type": "uint256"}
            ]
        }
        message_data = {
            "jobId": job_id_bytes32,
            "truthHash": truth_hash_hex,
            "mineralType": clean_mineral,
            "smelterId": smelter_id.strip().upper(),
            "conflictFree": human_rights_valid and conflict_risk_passed,
            "isValid": is_valid,
            "expiresAt": expires_at
        }
        signable_msg = encode_typed_data(full_message={
            "types": types,
            "primaryType": "MineralsTruthAttestation",
            "domain": domain_data,
            "message": message_data
        })
        signed = self.signer.account.sign_message(signable_msg)

        r_hex = "0x" + signed.r.to_bytes(32, "big").hex()
        s_hex = "0x" + signed.s.to_bytes(32, "big").hex()

        return {
            "domain": "CONFLICT_MINERALS",
            "domain_id": self.DOMAIN_INT,
            "job_id": job_id,
            "job_id_bytes32": job_id_bytes32,
            "mineral_type": clean_mineral,
            "smelter_id": smelter_id.strip().upper(),
            "smelter_audit_status": clean_smelter_status,
            "mine_country_code": mine_country_code.strip().upper(),
            "chain_of_custody_verified": coc_valid,
            "child_labor_free": human_rights_valid,
            "conflict_region": conflict_region,
            "enhanced_due_diligence": enhanced_due_diligence,
            "is_valid": is_valid,
            "truth_hash": truth_hash_hex,
            "signer": self.signer.signer_address,
            "expires_at": expires_at,
            "signature": {
                "r": r_hex,
                "s": s_hex,
                "v": signed.v,
                "full_signature": signed.signature.hex()
            },
            "rule_breakdown": {
                "mineral_supported": mineral_valid,
                "smelter_audited": smelter_valid,
                "chain_of_custody_confirmed": coc_valid,
                "human_rights_zero_tolerance_passed": human_rights_valid,
                "cahra_due_diligence_satisfied": conflict_risk_passed
            }
        }


minerals_truth_adapter = MineralsTruthAdapter()
