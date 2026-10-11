"""
Tier 3: Domain Truth Oracles & Extensions Plugin Subsystem.
===========================================================
Pluggable industry oracles and DeFi micro-services for Autonomous AI Agents.
- Global Trade & Maritime IoT
- Bio/Pharma IP ZK-SNARK Attestations
- Smart Construction & Drone LiDAR
- DePIN Energy & Compute
- Autonomous Mobility & E-Seal PoD
- FinTech: Factoring, Parametric Insurance, RWA Treasury
"""

from app.plugins.trade_oracle import (
    trade_iot_adapter,
    TradeIoTAdapter,
    eudr_truth_adapter,
    EudrTruthAdapter,
    minerals_truth_adapter,
    MineralsTruthAdapter,
)
from app.plugins.bio_oracle import (
    bio_zk_adapter,
    BioZkAdapter,
)
from app.plugins.construction_oracle import (
    build_drone_adapter,
    BuildDroneAdapter,
)
from app.plugins.depin_oracle import (
    power_grid_oracle,
    PowerGridOracle,
)
from app.plugins.fleet_pod_oracle import (
    autonomous_fleet_pod_oracle,
    AutonomousFleetPoDOracle,
)

__all__ = [
    "trade_iot_adapter",
    "TradeIoTAdapter",
    "eudr_truth_adapter",
    "EudrTruthAdapter",
    "minerals_truth_adapter",
    "MineralsTruthAdapter",
    "bio_zk_adapter",
    "BioZkAdapter",
    "build_drone_adapter",
    "BuildDroneAdapter",
    "power_grid_oracle",
    "PowerGridOracle",
    "autonomous_fleet_pod_oracle",
    "AutonomousFleetPoDOracle",
]
