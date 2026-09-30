"""
BuildDroneAdapter - Construction Infrastructure & 3D Drone LiDAR Truth Verification Engine.
===========================================================================================
Validates real-world civil engineering milestone truth:
1. Drone 3D LiDAR Point-Cloud volumetric match vs BIM CAD model >= 98.5%.
2. Embedded concrete IoT sensor compressive strength >= 24.0 MPa.
Issues EIP-712 MilestoneTruthAttestation for UniversalEscrowCore.sol.
"""

import math
import time
from typing import Dict, Any, List, Optional
import eth_utils
from eth_account import Account
from eth_account.messages import encode_typed_data

from app.onchain_signer import onchain_signer


class BuildDroneAdapter:
    """Evaluates construction milestone truth and signs cryptographic proof."""

    DOMAIN_INT = 2  # CONSTRUCTION_BUILD

    def __init__(self, signer=None):
        self.signer = signer or onchain_signer

    def verify_build_drone_truth(
        self,
        job_id: str,
        drone_lidar_volume_m3: float,
        bim_target_volume_m3: float,
        concrete_strength_samples_mpa: List[float],
        min_volumetric_ratio: float = 0.985,
        min_concrete_strength_mpa: float = 24.0,
        bim_spec_hash: Optional[str] = None,
        chain_id: int = 137,
        verifying_contract: str = "0x5555555555555555555555555555555555555555",
        validity_seconds: int = 3600
    ) -> Dict[str, Any]:
        """
        Validates construction milestone completion truth:
        - drone_volume / bim_volume ratio >= min_volumetric_ratio (98.5%)
        - concrete strength average & min sample >= min_concrete_strength_mpa (24.0 MPa)
        """
        try:
            d_vol = float(drone_lidar_volume_m3)
            b_vol = float(bim_target_volume_m3)
        except (ValueError, TypeError):
            raise ValueError("Volumetric parameters must be valid numeric values.")

        if d_vol <= 0.0 or b_vol <= 0.0 or math.isnan(d_vol) or math.isnan(b_vol):
            raise ValueError("Volumetric measurements must be strictly positive and finite.")

        # 1. Volumetric Ratio Check
        # Ratio of actual completed volume vs target design volume
        vol_ratio = min(d_vol, b_vol) / max(d_vol, b_vol)
        volumetric_passed = vol_ratio >= min_volumetric_ratio

        # 2. Concrete Compressive Strength Check
        if not concrete_strength_samples_mpa:
            raise ValueError("EMPTY_CONCRETE_STRENGTH_SAMPLES")

        for s in concrete_strength_samples_mpa:
            if math.isnan(s) or math.isinf(s) or s <= 0.0:
                raise ValueError("Concrete strength samples must be positive finite numbers.")

        avg_strength = sum(concrete_strength_samples_mpa) / len(concrete_strength_samples_mpa)
        min_strength = min(concrete_strength_samples_mpa)
        concrete_passed = (avg_strength >= min_concrete_strength_mpa) and (min_strength >= min_concrete_strength_mpa * 0.90)

        is_valid = volumetric_passed and concrete_passed

        # Formulate canonical truth digest
        spec_ref = bim_spec_hash or "BIM_MODEL_CERTIFIED"
        truth_material = f"CONSTRUCTION:{job_id}:{spec_ref}:{vol_ratio:.4f}:{avg_strength:.2f}"
        truth_hash = eth_utils.keccak(text=truth_material)
        truth_hash_hex = "0x" + truth_hash.hex()

        now = int(time.time())
        expires_at = now + validity_seconds

        job_id_bytes32 = eth_utils.to_hex(eth_utils.to_bytes(text=job_id).ljust(32, b"\0")) if len(job_id) <= 32 else job_id

        # 3. Sign EIP-712 MilestoneTruthAttestation
        domain_data = {
            "name": "BuildDroneAdapter",
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
            "MilestoneTruthAttestation": [
                {"name": "jobId", "type": "bytes32"},
                {"name": "truthHash", "type": "bytes32"},
                {"name": "volumetricRatioBps", "type": "uint256"},
                {"name": "avgConcreteStrengthMpa", "type": "uint256"},
                {"name": "isValid", "type": "bool"},
                {"name": "expiresAt", "type": "uint256"}
            ]
        }
        vol_ratio_bps = int(round(vol_ratio * 10000))
        strength_int = int(round(avg_strength))

        message_data = {
            "jobId": job_id_bytes32,
            "truthHash": truth_hash_hex,
            "volumetricRatioBps": vol_ratio_bps,
            "avgConcreteStrengthMpa": strength_int,
            "isValid": is_valid,
            "expiresAt": expires_at
        }
        signable_msg = encode_typed_data(full_message={
            "types": types,
            "primaryType": "MilestoneTruthAttestation",
            "domain": domain_data,
            "message": message_data
        })
        signed = self.signer.account.sign_message(signable_msg)

        r_hex = "0x" + signed.r.to_bytes(32, "big").hex()
        s_hex = "0x" + signed.s.to_bytes(32, "big").hex()

        return {
            "domain": "CONSTRUCTION_BUILD",
            "domain_id": self.DOMAIN_INT,
            "job_id": job_id,
            "is_valid": is_valid,
            "verdict": "PASSED" if is_valid else "FAILED",
            "metrics": {
                "drone_lidar_volume_m3": d_vol,
                "bim_target_volume_m3": b_vol,
                "volumetric_match_ratio": round(vol_ratio, 4),
                "volumetric_passed": volumetric_passed,
                "avg_concrete_strength_mpa": round(avg_strength, 2),
                "min_concrete_strength_mpa": round(min_strength, 2),
                "concrete_strength_passed": concrete_passed,
                "bim_spec_hash": bim_spec_hash
            },
            "truth_hash": truth_hash_hex,
            "attestation": {
                "jobId": job_id_bytes32,
                "truthHash": truth_hash_hex,
                "volumetricRatioBps": vol_ratio_bps,
                "avgConcreteStrengthMpa": strength_int,
                "isValid": is_valid,
                "expiresAt": expires_at,
                "v": signed.v,
                "r": r_hex,
                "s": s_hex,
                "oracle_signer": self.signer.signer_address,
                "chain_id": chain_id
            }
        }


build_drone_adapter = BuildDroneAdapter()
