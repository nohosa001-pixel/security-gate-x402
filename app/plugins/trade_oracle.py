"""
Agent Security Gate x402 - Plugin: Global Trade & Logistics Truth Oracle
========================================================================
Integrates Maritime IoT, Cold-Chain telemetry, GPS geofencing, EUDR, and Conflict Minerals.
"""

from app.truth_adapters.trade_iot_adapter import trade_iot_adapter, TradeIoTAdapter
from app.truth_adapters.eudr_truth_adapter import eudr_truth_adapter, EudrTruthAdapter
from app.truth_adapters.minerals_truth_adapter import minerals_truth_adapter, MineralsTruthAdapter

__all__ = [
    "trade_iot_adapter",
    "TradeIoTAdapter",
    "eudr_truth_adapter",
    "EudrTruthAdapter",
    "minerals_truth_adapter",
    "MineralsTruthAdapter"
]
