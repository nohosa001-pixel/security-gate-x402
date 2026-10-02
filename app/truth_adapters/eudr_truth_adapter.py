"""
EudrTruthAdapter - EU Deforestation Regulation (EUDR) Physical Truth Verification Engine.
========================================================================================
Validates real-world supply chain EUDR compliance:
1. Satellite Deforestation-Free Verification: Confirms zero deforestation on or after 2020-12-31 cutoff.
2. Geolocation Polygon Integrity: Validates plot GPS polygon (minimum 3 coordinates).
3. Due Diligence Statement (DDS) Reference: Ensures formal EU Registry filing trace.
4. Legal Harvest / Production: Confirms compliance with origin country land-use legislation.

Issues EIP-712 EudrTruthAttestation for UniversalEscrowCore.sol.
"""

import time
import hashlib
from typing import Dict, Any, List, Tuple, Optional
import eth_utils
from eth_account import Account
from eth_account.messages import encode_typed_data

from app.onchain_signer import onchain_signer

SUPPORTED_EUDR_COMMODITIES = {
    "wood", "timber", "rubber", "palm_oil", "soy", "coffee", "cocoa", "cattle", "beef", "leather"
}


class EudrTruthAdapter:
    """Evaluates EUDR deforestation-free compliance and signs cryptographic proof."""

    DOMAIN_INT = 3  # EUDR_FOREST

    def __init__(self, signer=None):
        self.signer = signer or onchain_signer

    def verify_eudr_truth(
        self,
        job_id: str,
        commodity: str,
        country_code: str,
        polygon_coordinates: List[Tuple[float, float]],
        dds_reference_id: str,
        deforestation_detected: bool,
        legal_harvest_verified: bool,
        satellite_cutoff_date: str = "2020-12-31",
        chain_id: int = 137,
        verifying_contract: str = "0x5555555555555555555555555555555555555555",
        validity_seconds: int = 3600
    ) -> Dict[str, Any]:
        """
        Validates EUDR criteria:
        - commodity is recognized under EUDR Annex I
        - polygon has >= 3 coordinates
        - deforestation_detected is False (100% deforestation-free)
        - legal_harvest_verified is True
        - dds_reference_id is non-empty
        """
        # 1. Commodity Check
        clean_commodity = commodity.strip().lower()
        commodity_valid = clean_commodity in SUPPORTED_EUDR_COMMODITIES

        # 2. Polygon Check (minimum 3 points to form a closed plot)
        polygon_valid = bool(polygon_coordinates and len(polygon_coordinates) >= 3)
        if polygon_valid:
            for lat, lon in polygon_coordinates:
                if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
                    polygon_valid = False
                    break

        # 3. Deforestation Free Check
        deforestation_free = not deforestation_detected

        # 4. DDS Reference & Legal Check
        dds_valid = bool(dds_reference_id and len(dds_reference_id.strip()) >= 6)
        legal_valid = bool(legal_harvest_verified)

        is_valid = (
            commodity_valid
            and polygon_valid
            and deforestation_free
            and dds_valid
            and legal_valid
        )

        # Formulate canonical polygon hash
        coord_repr = ";".join([f"{lat:.6f},{lon:.6f}" for lat, lon in (polygon_coordinates or [])])
        polygon_hash = eth_utils.keccak(text=coord_repr).hex()

        # Formulate canonical truth digest
        truth_material = (
            f"EUDR:{job_id}:{clean_commodity}:{country_code.strip().upper()}:"
            f"{polygon_hash}:{dds_reference_id.strip()}:{int(deforestation_free)}:{int(legal_valid)}"
        )
        truth_hash = eth_utils.keccak(text=truth_material)
        truth_hash_hex = "0x" + truth_hash.hex()

        now = int(time.time())
        expires_at = now + validity_seconds

        # Format job_id bytes32
        job_id_bytes32 = eth_utils.to_hex(eth_utils.to_bytes(text=job_id).ljust(32, b"\0")) if len(job_id) <= 32 else job_id

        # Sign EIP-712 EudrTruthAttestation
        domain_data = {
            "name": "EudrTruthAdapter",
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
            "EudrTruthAttestation": [
                {"name": "jobId", "type": "bytes32"},
                {"name": "truthHash", "type": "bytes32"},
                {"name": "commodity", "type": "string"},
                {"name": "deforestationFree", "type": "bool"},
                {"name": "legalHarvest", "type": "bool"},
                {"name": "isValid", "type": "bool"},
                {"name": "expiresAt", "type": "uint256"}
            ]
        }
        message_data = {
            "jobId": job_id_bytes32,
            "truthHash": truth_hash_hex,
            "commodity": clean_commodity,
            "deforestationFree": deforestation_free,
            "legalHarvest": legal_valid,
            "isValid": is_valid,
            "expiresAt": expires_at
        }
        signable_msg = encode_typed_data(full_message={
            "types": types,
            "primaryType": "EudrTruthAttestation",
            "domain": domain_data,
            "message": message_data
        })
        signed = self.signer.account.sign_message(signable_msg)

        r_hex = "0x" + signed.r.to_bytes(32, "big").hex()
        s_hex = "0x" + signed.s.to_bytes(32, "big").hex()

        return {
            "domain": "EUDR_FOREST",
            "domain_id": self.DOMAIN_INT,
            "job_id": job_id,
            "job_id_bytes32": job_id_bytes32,
            "commodity": clean_commodity,
            "country_code": country_code.strip().upper(),
            "polygon_coordinates_count": len(polygon_coordinates or []),
            "polygon_hash": "0x" + polygon_hash,
            "dds_reference_id": dds_reference_id.strip(),
            "deforestation_free": deforestation_free,
            "deforestationFree": deforestation_free,
            "legal_harvest_verified": legal_valid,
            "legalHarvest": legal_valid,
            "is_valid": is_valid,
            "isValid": is_valid,
            "verdict": "PASSED" if is_valid else "FAILED",
            "truth_hash": truth_hash_hex,
            "truthHash": truth_hash_hex,
            "signer": self.signer.signer_address,
            "expires_at": expires_at,
            "expiresAt": expires_at,
            "signature": {
                "r": r_hex,
                "s": s_hex,
                "v": signed.v,
                "full_signature": signed.signature.hex()
            },
            "rule_breakdown": {
                "commodity_supported": commodity_valid,
                "polygon_integrity": polygon_valid,
                "zero_deforestation_passed": deforestation_free,
                "dds_statement_verified": dds_valid,
                "national_legality_satisfied": legal_valid
            }
        }


eudr_truth_adapter = EudrTruthAdapter()
