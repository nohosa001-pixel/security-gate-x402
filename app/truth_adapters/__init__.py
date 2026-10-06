"""
A.GRID Universal Modular Truth Adapters Package.
Provides deterministic physical & mathematical truth evaluation engines for:
1. Maritime Freight IoT (GPS Geofence + Cold-Chain Temperature Log)
2. Bio / Pharma ZK (Genomic Merkle Root + Binding Affinity Kd ZK-Proof)
3. Construction Infrastructure Drone (3D LiDAR BIM Matching + Concrete Strength Sensor)
"""

from app.truth_adapters.trade_iot_adapter import TradeIoTAdapter, trade_iot_adapter
from app.truth_adapters.bio_zk_adapter import BioZkAdapter, bio_zk_adapter
from app.truth_adapters.build_drone_adapter import BuildDroneAdapter, build_drone_adapter
from app.truth_adapters.eudr_truth_adapter import EudrTruthAdapter, eudr_truth_adapter
from app.truth_adapters.minerals_truth_adapter import MineralsTruthAdapter, minerals_truth_adapter
from app.truth_adapters.zktls_web_proof_adapter import ZkTLSWebProofAdapter, zktls_adapter

__all__ = [
    "TradeIoTAdapter",
    "trade_iot_adapter",
    "BioZkAdapter",
    "bio_zk_adapter",
    "BuildDroneAdapter",
    "build_drone_adapter",
    "EudrTruthAdapter",
    "eudr_truth_adapter",
    "MineralsTruthAdapter",
    "minerals_truth_adapter",
    "ZkTLSWebProofAdapter",
    "zktls_adapter"
]
