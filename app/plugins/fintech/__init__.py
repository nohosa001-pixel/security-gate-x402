"""
Tier 3: DeFi & FinTech Extensions Plugin Subsystem.
===================================================
Provides Factoring, Parametric Insurance, and RWA Treasury management.
"""

from app.plugins.fintech.factoring import (
    UniversalFactoringBridge,
    universal_factoring_bridge,
    AgentFactoringEngine,
    factoring_engine
)
from app.plugins.fintech.insurance import (
    UniversalInsuranceBridge,
    universal_insurance_bridge,
    AgentInsuranceEngine,
    insurance_engine
)
from app.plugins.fintech.rwa_treasury import (
    SovereignTreasuryEngine,
    sovereign_treasury
)

__all__ = [
    "UniversalFactoringBridge",
    "universal_factoring_bridge",
    "AgentFactoringEngine",
    "factoring_engine",
    "UniversalInsuranceBridge",
    "universal_insurance_bridge",
    "AgentInsuranceEngine",
    "insurance_engine",
    "SovereignTreasuryEngine",
    "sovereign_treasury"
]
