"""
Agent Security Gate x402 - FinTech Plugin: Factoring
====================================================
Exposes receivables factoring, discount rate calculation, and EIP-712 bond attestations.
"""

from app.universal_factoring_bridge import (
    UniversalFactoringBridge,
    universal_factoring_bridge,
    AgentFactoringEngine,
    factoring_engine,
    FACTORING_POOLS,
    UNIVERSAL_ESCROWS
)

__all__ = [
    "UniversalFactoringBridge",
    "universal_factoring_bridge",
    "AgentFactoringEngine",
    "factoring_engine",
    "FACTORING_POOLS",
    "UNIVERSAL_ESCROWS"
]
