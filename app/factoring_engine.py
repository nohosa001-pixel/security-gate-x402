"""
Agent Security Gate x402 - Agent Receivables Factoring Engine Facade.
=====================================================================
Consolidated into `app.universal_factoring_bridge`.
Maintains 100% backward-compatible imports for AgentFactoringEngine & factoring_engine.
"""

from app.universal_factoring_bridge import (
    AgentFactoringEngine,
    factoring_engine,
    UniversalFactoringBridge,
    universal_factoring_bridge
)

__all__ = [
    "AgentFactoringEngine",
    "factoring_engine",
    "UniversalFactoringBridge",
    "universal_factoring_bridge"
]
