"""
Agent Security Gate x402 - FinTech Plugin: RWA Treasury & Proof-of-Reserves
============================================================================
Exposes autonomous rebalancing across T-Bills (BUIDL/USDY) and Merkle PoR attestations.
"""

from app.rwa_treasury_engine import (
    SovereignTreasuryEngine,
    sovereign_treasury,
    RWA_ASSET_REGISTRY
)

__all__ = [
    "SovereignTreasuryEngine",
    "sovereign_treasury",
    "RWA_ASSET_REGISTRY"
]
