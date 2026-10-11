"""
Agent Security Gate x402 - Agent Malpractice & Failure Insurance Facade.
========================================================================
Consolidated into `app.universal_insurance_bridge`.
Maintains 100% backward-compatible imports for AgentInsuranceEngine & insurance_engine.
"""

from app.universal_insurance_bridge import (
    AgentInsuranceEngine,
    insurance_engine,
    UniversalInsuranceBridge,
    universal_insurance_bridge
)

__all__ = [
    "AgentInsuranceEngine",
    "insurance_engine",
    "UniversalInsuranceBridge",
    "universal_insurance_bridge"
]
