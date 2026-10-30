"""Unit and Integration Tests for AutonomousCrossRailRouter (Phase 2).

Verifies:
1. Pool initialization and target weight distribution across Solana (501) and EVM rails.
2. Deficit and Surplus detection under dynamic agent streaming settlement demand.
3. Circle CCTP route planning with zero-slippage and protocol toll calculation.
4. Cryptographic HMAC/SHA-256 Oracle Attestation security and tamper resistance.
5. Safety Invariants: Single Rebalance Cap ($50k) and 24h Velocity Ceiling ($250k).
6. End-to-end execution of cross-rail liquidity rebalancing from Base to Solana.
"""

import pytest
from app.cross_rail_liquidity_router import (
    AutonomousCrossRailRouter,
    BridgeProtocol,
    ChainLiquidityPool,
    RebalanceRoute,
)


@pytest.fixture
def router():
    """Initializes router with standard test oracle key."""
    return AutonomousCrossRailRouter(oracle_signing_key="test_cross_rail_secret_key_123")


def test_pool_initialization_and_weights(router):
    """Test initial state across 4 major chains."""
    summary = router.get_fleet_liquidity_summary()
    assert summary["total_reserve_usdc"] == 250_000.0
    assert 501 in summary["chains"]
    assert 8453 in summary["chains"]
    assert 137 in summary["chains"]
    assert 42161 in summary["chains"]

    # Check Solana specific free liquidity: 45k reserve - 30k escrow = 15k free
    solana_pool = router.pools[501]
    assert solana_pool.free_liquidity_usdc == 15_000.0


def test_fleet_summary_and_deficit_detection(router):
    """Test that Solana is flagged as DEFICIT due to high pending demand and Base as SURPLUS."""
    deficit_pools, surplus_pools = router.detect_imbalances()
    deficit_ids = [p.chain_id for p in deficit_pools]
    surplus_ids = [p.chain_id for p in surplus_pools]

    assert 501 in deficit_ids, "Solana should be in DEFICIT state"
    assert 8453 in surplus_ids, "Base should be in SURPLUS state"


def test_plan_rebalance_routes_cctp(router):
    """Test formulation of Circle CCTP rebalance route from Base to Solana."""
    routes = router.plan_rebalance_routes()
    assert len(routes) >= 1

    primary_route = routes[0]
    assert primary_route.source_chain_id == 8453
    assert primary_route.target_chain_id == 501
    assert primary_route.bridge_protocol == BridgeProtocol.CIRCLE_CCTP
    assert primary_route.slippage_percent == 0.0
    assert primary_route.amount_usdc > 0
    assert primary_route.bridge_toll_usdc > 0
    assert len(primary_route.proof_hash) == 64  # SHA-256


def test_cryptographic_attestation_verification(router):
    """Test that valid attestation passes and tampered route fails verification."""
    routes = router.plan_rebalance_routes()
    route = routes[0]

    # Valid check
    assert router.verify_rebalance_attestation(route) is True

    # Tampered amount check
    tampered_route = RebalanceRoute(
        route_id=route.route_id,
        source_chain_id=route.source_chain_id,
        source_chain_name=route.source_chain_name,
        target_chain_id=route.target_chain_id,
        target_chain_name=route.target_chain_name,
        amount_usdc=route.amount_usdc + 1000.0,  # Unauthorized modification
        bridge_protocol=route.bridge_protocol,
        estimated_latency_seconds=route.estimated_latency_seconds,
        bridge_toll_usdc=route.bridge_toll_usdc,
        slippage_percent=route.slippage_percent,
        proof_hash=route.proof_hash,
        timestamp=route.timestamp
    )
    assert router.verify_rebalance_attestation(tampered_route) is False


def test_single_tx_cap_enforcement(router):
    """Test that single rebalance exceeding $50k is strictly rejected."""
    routes = router.plan_rebalance_routes()
    route = routes[0]
    route.amount_usdc = 60_000.0  # Exceeds 50k cap

    with pytest.raises(Exception):
        router.execute_rebalance(route)


def test_daily_cap_enforcement(router):
    """Test that cumulative 24h rebalance exceeding $250k is strictly blocked."""
    router.cumulative_24h_rebalance_usdc = 240_000.0
    routes = router.plan_rebalance_routes()
    route = routes[0]
    route.amount_usdc = 15_000.0  # 240k + 15k = 255k > 250k cap

    # Re-sign for 15k to pass signature check
    route.timestamp = 1700000000
    import hashlib
    import hmac
    payload = f"{route.source_chain_id}->{route.target_chain_id}:{route.amount_usdc}:{route.bridge_protocol.value}:{route.timestamp}"
    route.proof_hash = hmac.new(router.oracle_key, payload.encode("utf-8"), hashlib.sha256).hexdigest()

    with pytest.raises(ValueError, match="24h cumulative limit"):
        router.execute_rebalance(route)


def test_end_to_end_rebalance_execution(router):
    """Test complete successful rebalancing cycle from Base (8453) to Solana (501)."""
    initial_solana_reserve = router.pools[501].reserve_usdc
    initial_solana_demand = router.pools[501].pending_demand_usdc

    routes = router.plan_rebalance_routes()
    assert len(routes) > 0
    route = routes[0]

    result = router.execute_rebalance(route)

    assert result["status"] == "SETTLED"
    assert result["source_chain"] == "Base Mainnet"
    assert result["target_chain"] == "Solana Mainnet"
    assert router.pools[501].reserve_usdc > initial_solana_reserve
    assert router.pools[501].pending_demand_usdc < initial_solana_demand
    assert router.cumulative_24h_rebalance_usdc == route.amount_usdc


def test_api_endpoints_liquidity_lifecycle():
    """Test full HTTP API lifecycle via FastAPI TestClient."""
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)

    # 1. Summary
    resp = client.get("/api/v1/liquidity/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_reserve_usdc" in data
    assert "chains" in data

    # 2. Plan
    resp = client.post("/api/v1/liquidity/rebalance/plan")
    assert resp.status_code == 200
    plan_data = resp.json()
    assert plan_data["status"] == "SUCCESS"
    assert len(plan_data["routes"]) >= 1
    target_route = plan_data["routes"][0]

    # 3. Unauthorized Execution (Forged Hash)
    bad_payload = dict(target_route)
    bad_payload["proof_hash"] = "0000000000000000000000000000000000000000000000000000000000000000"
    resp = client.post("/api/v1/liquidity/rebalance/execute", json=bad_payload)
    assert resp.status_code == 403

    # 4. Valid Execution
    resp = client.post("/api/v1/liquidity/rebalance/execute", json=target_route)
    assert resp.status_code == 200
    exec_data = resp.json()
    assert exec_data["status"] == "SETTLED"
    assert exec_data["amount_dispatched_usdc"] > 0


def test_plan_rebalance_polygon_oms_to_solana(router):
    """Test that when Polygon (137) has surplus and Solana (501) has deficit, Polygon OMS is selected."""
    router.update_pool_reserve(137, reserve_usdc=150_000.0, reserved_in_escrow_usdc=10_000.0, pending_demand_usdc=0.0)
    router.update_pool_reserve(8453, reserve_usdc=40_000.0, reserved_in_escrow_usdc=30_000.0, pending_demand_usdc=10_000.0)
    router.update_pool_reserve(501, reserve_usdc=20_000.0, reserved_in_escrow_usdc=15_000.0, pending_demand_usdc=30_000.0)

    routes = router.plan_rebalance_routes()
    assert len(routes) >= 1

    oms_route = next((r for r in routes if r.source_chain_id == 137 and r.target_chain_id == 501), None)
    assert oms_route is not None
    assert oms_route.bridge_protocol == BridgeProtocol.POLYGON_OMS
    assert oms_route.estimated_latency_seconds == 1.2
    assert oms_route.slippage_percent == 0.0


