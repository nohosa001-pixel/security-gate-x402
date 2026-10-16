"""
LogisticsTruthAdapter - DCSA eBL v3.0 & GS1 EPCIS 2.0 Delivery Truth Engine.
=============================================================================
Validates real-world container shipment & supply chain logistics truth:
1. DCSA eBL v3.0 electronic bill of lading & ISO 6346 container number format.
2. IMO vessel number validity & AIS transit tracking.
3. Cold-chain / transit environmental telemetry Merkle Root calculation.
4. Generates EIP-712 ProofOfDelivery attestation compatible with LogisticsPoDEscrow.sol.
"""

from typing import Dict, Any, List, Optional
from eth_account import Account
from logistics_oracle_mcp import LogisticsVerificationEngine, default_engine


class LogisticsTruthAdapter:
    """Evaluates maritime/multimodal logistics delivery truth and signs cryptographic proof."""

    DOMAIN_INT = 6  # LOGISTICS_POD

    def __init__(self, engine: Optional[LogisticsVerificationEngine] = None):
        self.engine = engine or default_engine

    def verify_ebl(
        self,
        bl_number: str,
        carrier_scac: str,
        vessel_imo: int,
        container_id: str,
        origin_port: str,
        dest_port: str
    ) -> Dict[str, Any]:
        """Validates DCSA eBL v3.0 standard parameters."""
        return self.engine.verify_dcsa_ebl(
            bl_number=bl_number,
            carrier_scac=carrier_scac,
            vessel_imo=vessel_imo,
            container_id=container_id,
            origin_port=origin_port,
            dest_port=dest_port
        )

    def audit_telemetry(
        self,
        sensor_logs: List[Dict[str, Any]],
        max_allowed_temp_c: float = 25.0,
        min_allowed_temp_c: Optional[float] = None
    ) -> Dict[str, Any]:
        """Audits sensor logs and calculates Merkle Root."""
        return self.engine.audit_telemetry(
            sensor_logs=sensor_logs,
            max_allowed_temp_c=max_allowed_temp_c,
            min_allowed_temp_c=min_allowed_temp_c
        )

    def issue_pod_attestation(
        self,
        deal_id: str,
        bl_document_hash: str,
        container_id: str,
        vessel_imo: int,
        dest_unlocode: str,
        sensor_logs: List[Dict[str, Any]],
        max_allowed_temp_c: float = 25.0,
        min_allowed_temp_c: Optional[float] = None
    ) -> Dict[str, Any]:
        """Issues EIP-712 Proof-of-Delivery attestation for on-chain settlement."""
        return self.engine.issue_pod_attestation(
            deal_id_hex=deal_id,
            bl_doc_hash=bl_document_hash,
            container_id=container_id,
            vessel_imo=vessel_imo,
            dest_unlocode=dest_unlocode,
            sensor_logs=sensor_logs,
            max_allowed_temp_c=max_allowed_temp_c,
            min_allowed_temp_c=min_allowed_temp_c
        )


logistics_truth_adapter = LogisticsTruthAdapter()
