"""
Agent Security Gate x402 - FinTech Plugin: Parametric Insurance & Slashing
===========================================================================
Exposes parametric risk underwriting, claim adjudication, and automatic stake slashing.
"""

from app.universal_insurance_bridge import (
    UniversalInsuranceBridge,
    universal_insurance_bridge,
    AgentInsuranceEngine,
    insurance_engine,
    INSURANCE_POOLS,
    BASE_RISK_BPS
)

__all__ = [
    "UniversalInsuranceBridge",
    "universal_insurance_bridge",
    "AgentInsuranceEngine",
    "insurance_engine",
    "INSURANCE_POOLS",
    "BASE_RISK_BPS"
]
