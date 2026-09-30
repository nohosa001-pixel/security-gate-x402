"""
TradeIoTAdapter - Global Maritime Freight & Cold-Chain IoT Truth Verification Engine.
=====================================================================================
Validates real-world shipping delivery truth:
1. Haversine Satellite GPS Geofencing (within 500m of destination port coordinates).
2. Cold-Chain Invariant: Contiguous temperature timeseries within -20°C ± 2°C (-22°C to -18°C).
3. RFID Port Automated Unloading Tag Match.
Issues EIP-712 MaritimeTruthAttestation for UniversalEscrowCore.sol.
"""

import math
import time
from typing import Dict, Any, List, Tuple, Optional
import eth_utils
from eth_account import Account
from eth_account.messages import encode_typed_data

from app.onchain_signer import onchain_signer


def haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Computes great-circle distance between two GPS coordinates in meters."""
    R = 6371000.0  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2))
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c


class TradeIoTAdapter:
    """Evaluates maritime cargo delivery truth and signs cryptographic proof."""

    DOMAIN_INT = 0  # TRADE_MARITIME

    def __init__(self, signer=None):
        self.signer = signer or onchain_signer

    def verify_maritime_truth(
        self,
        job_id: str,
        current_gps: Tuple[float, float],
        destination_port_gps: Tuple[float, float],
        temperature_timeseries_celsius: List[float],
        rfid_tag: str,
        expected_rfid_tag: str,
        max_geofence_radius_meters: float = 500.0,
        temp_min_celsius: float = -22.0,
        temp_max_celsius: float = -18.0,
        chain_id: int = 137,
        verifying_contract: str = "0x5555555555555555555555555555555555555555",
        validity_seconds: int = 3600
    ) -> Dict[str, Any]:
        """
        Validates shipping truth:
        - GPS distance <= max_geofence_radius_meters
        - All temperatures between temp_min_celsius and temp_max_celsius
        - RFID tag matches expected
        """
        lat_curr, lon_curr = current_gps
        lat_dest, lon_dest = destination_port_gps

        # 1. Geofence Distance Check
        distance_m = haversine_distance_meters(lat_curr, lon_curr, lat_dest, lon_dest)
        geofence_passed = distance_m <= max_geofence_radius_meters

        # 2. Cold-Chain Temperature Check
        if not temperature_timeseries_celsius:
            raise ValueError("EMPTY_TEMPERATURE_SERIES")

        temp_min_observed = min(temperature_timeseries_celsius)
        temp_max_observed = max(temperature_timeseries_celsius)
        temp_violations = [t for t in temperature_timeseries_celsius if t < temp_min_celsius or t > temp_max_celsius]
        cold_chain_passed = len(temp_violations) == 0

        # 3. RFID Check
        rfid_passed = str(rfid_tag).strip().upper() == str(expected_rfid_tag).strip().upper()

        is_valid = geofence_passed and cold_chain_passed and rfid_passed

        # Formulate canonical truth digest
        truth_material = (
            f"MARITIME:{job_id}:{distance_m:.2f}:{temp_min_observed:.2f}:"
            f"{temp_max_observed:.2f}:{rfid_tag.strip().upper()}"
        )
        truth_hash = eth_utils.keccak(text=truth_material)
        truth_hash_hex = "0x" + truth_hash.hex()

        now = int(time.time())
        expires_at = now + validity_seconds

        # Format job_id bytes32
        job_id_bytes32 = eth_utils.to_hex(eth_utils.to_bytes(text=job_id).ljust(32, b"\0")) if len(job_id) <= 32 else job_id

        # 4. Sign EIP-712 MaritimeTruthAttestation
        domain_data = {
            "name": "TradeIoTAdapter",
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
            "MaritimeTruthAttestation": [
                {"name": "jobId", "type": "bytes32"},
                {"name": "truthHash", "type": "bytes32"},
                {"name": "geofenceDistanceMeters", "type": "uint256"},
                {"name": "isValid", "type": "bool"},
                {"name": "expiresAt", "type": "uint256"}
            ]
        }
        message_data = {
            "jobId": job_id_bytes32,
            "truthHash": truth_hash_hex,
            "geofenceDistanceMeters": int(round(distance_m)),
            "isValid": is_valid,
            "expiresAt": expires_at
        }
        signable_msg = encode_typed_data(full_message={
            "types": types,
            "primaryType": "MaritimeTruthAttestation",
            "domain": domain_data,
            "message": message_data
        })
        signed = self.signer.account.sign_message(signable_msg)

        r_hex = "0x" + signed.r.to_bytes(32, "big").hex()
        s_hex = "0x" + signed.s.to_bytes(32, "big").hex()

        return {
            "domain": "TRADE_MARITIME",
            "domain_id": self.DOMAIN_INT,
            "job_id": job_id,
            "is_valid": is_valid,
            "verdict": "PASSED" if is_valid else "FAILED",
            "metrics": {
                "distance_to_port_meters": round(distance_m, 2),
                "geofence_passed": geofence_passed,
                "temp_min_celsius": temp_min_observed,
                "temp_max_celsius": temp_max_observed,
                "temp_violations_count": len(temp_violations),
                "cold_chain_passed": cold_chain_passed,
                "rfid_matched": rfid_passed
            },
            "truth_hash": truth_hash_hex,
            "attestation": {
                "jobId": job_id_bytes32,
                "truthHash": truth_hash_hex,
                "geofenceDistanceMeters": int(round(distance_m)),
                "isValid": is_valid,
                "expiresAt": expires_at,
                "v": signed.v,
                "r": r_hex,
                "s": s_hex,
                "oracle_signer": self.signer.signer_address,
                "chain_id": chain_id
            }
        }


trade_iot_adapter = TradeIoTAdapter()
