"""
Unit and Integration Tests for V2 Deployment Infrastructure
===========================================================
Validates:
1. Compiled ABI and Bytecode presence and integrity for AgenticShieldPool & LogisticsPoDEscrow.
2. Web3 constructor ABI parameter encoding across Base (8453), Polygon (137), Arbitrum (42161).
3. Dry-run simulation plan generation and parameter conformance.
"""

import pytest
from web3 import Web3
from scripts.deploy_v2_infrastructure import (
    load_contract_artifact,
    build_deployment_plan,
    run_deployment,
    NETWORK_CONFIGS
)


def test_v2_contract_artifacts_integrity():
    """Confirms that compiled artifacts exist and have non-empty ABI & bytecode."""
    shield_abi, shield_bin = load_contract_artifact("AgenticShieldPool")
    assert isinstance(shield_abi, list)
    assert len(shield_abi) > 20
    assert shield_bin.startswith("0x")
    assert len(shield_bin) > 5000

    logistics_abi, logistics_bin = load_contract_artifact("LogisticsPoDEscrow")
    assert isinstance(logistics_abi, list)
    assert len(logistics_abi) > 10
    assert logistics_bin.startswith("0x")
    assert len(logistics_bin) > 3000


@pytest.mark.parametrize("chain_key", ["base", "polygon", "arbitrum"])
def test_v2_deployment_plan_and_constructor_encoding(chain_key):
    """
    Validates that constructor parameters for each chain are valid checksummed addresses
    and encode into valid EVM deployment calldata without errors.
    """
    plan = build_deployment_plan(chain_key)
    assert plan["chain_id"] == NETWORK_CONFIGS[chain_key]["chain_id"]
    assert "AgenticShieldPool" in plan["contracts"]
    assert "LogisticsPoDEscrow" in plan["contracts"]

    w3 = Web3()
    # 1. Test AgenticShieldPool constructor encoding
    shield_data = plan["contracts"]["AgenticShieldPool"]
    shield_contract = w3.eth.contract(abi=shield_data["abi"], bytecode=shield_data["bytecode"])
    tx_shield = shield_contract.constructor(*shield_data["constructor_args"]).build_transaction({
        "from": "0xA185B43fDD19619f99952AAed6eabf1029bF36a1",
        "nonce": 0,
        "gas": 3000000,
        "gasPrice": 1000000000,
        "chainId": plan["chain_id"]
    })
    assert len(tx_shield["data"]) > 10000

    # 2. Test LogisticsPoDEscrow constructor encoding
    logistics_data = plan["contracts"]["LogisticsPoDEscrow"]
    logistics_contract = w3.eth.contract(abi=logistics_data["abi"], bytecode=logistics_data["bytecode"])
    tx_logistics = logistics_contract.constructor(*logistics_data["constructor_args"]).build_transaction({
        "from": "0xA185B43fDD19619f99952AAed6eabf1029bF36a1",
        "nonce": 0,
        "gas": 3000000,
        "gasPrice": 1000000000,
        "chainId": plan["chain_id"]
    })
    assert len(tx_logistics["data"]) > 5000


def test_dry_run_simulation_execution():
    """Runs dry-run deployment simulation and asserts success status."""
    res = run_deployment("base", dry_run=True)
    assert res["status"] == "SIMULATED_SUCCESS"
    assert res["chain_key"] == "base"
    assert res["contracts"]["AgenticShieldPool"]["verified"] is True
    assert res["contracts"]["LogisticsPoDEscrow"]["verified"] is True
