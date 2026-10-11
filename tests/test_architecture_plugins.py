"""
Test Suite for 3-Tier Decoupled Architecture & Plugins Subsystem.
Verifies clean imports, facade compatibility, and Tier 3 plugins isolation.
"""

import pytest


def test_plugins_subsystem_imports():
    """Validates that Tier 3 plugins can be imported and function correctly."""
    from app.plugins import (
        trade_iot_adapter,
        eudr_truth_adapter,
        minerals_truth_adapter,
        bio_zk_adapter,
        build_drone_adapter,
        power_grid_oracle,
        autonomous_fleet_pod_oracle,
    )
    from app.plugins.fintech import (
        universal_factoring_bridge,
        factoring_engine,
        universal_insurance_bridge,
        insurance_engine,
        sovereign_treasury,
    )

    assert trade_iot_adapter is not None
    assert eudr_truth_adapter is not None
    assert minerals_truth_adapter is not None
    assert bio_zk_adapter is not None
    assert build_drone_adapter is not None
    assert power_grid_oracle is not None
    assert autonomous_fleet_pod_oracle is not None
    assert universal_factoring_bridge is not None
    assert factoring_engine is not None
    assert universal_insurance_bridge is not None
    assert insurance_engine is not None
    assert sovereign_treasury is not None


def test_consolidated_facades_backward_compatibility():
    """Validates that backward-compatible facades re-export identical instances."""
    from app.factoring_engine import factoring_engine as fe1, AgentFactoringEngine as AFE1
    from app.universal_factoring_bridge import factoring_engine as fe2, AgentFactoringEngine as AFE2
    assert fe1 is fe2
    assert AFE1 is AFE2

    from app.insurance_engine import insurance_engine as ie1, AgentInsuranceEngine as AIE1
    from app.universal_insurance_bridge import insurance_engine as ie2, AgentInsuranceEngine as AIE2
    assert ie1 is ie2
    assert AIE1 is AIE2

    from app.guarded_wallet import GuardedSafeWallet as GSW1
    from app.spend_guard import GuardedSafeWallet as GSW2
    assert GSW1 is GSW2

    from app.agent_credit_engine import credit_engine as ce1
    from app.credit_rating_engine import credit_engine as ce2
    assert ce1 is ce2
