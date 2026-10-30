"""Cross-Rail Autonomous Liquidity Router API (Phase 2).

Provides programmatic endpoints for autonomous agents, solvency monitors, and
fleet treasuries to inspect multi-chain liquidity across Solana (501), Base (8453),
Polygon (137), and Arbitrum (42161), and execute Circle CCTP rebalances.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.cross_rail_liquidity_router import (
    AutonomousCrossRailRouter,
    BridgeProtocol,
    RebalanceRoute,
)

router = APIRouter(prefix="/api/v1/liquidity", tags=["Cross-Rail Liquidity Router"])

# Singleton router instance for the application runtime
cross_rail_router = AutonomousCrossRailRouter()


class PoolUpdateRequest(BaseModel):
    chain_id: int = Field(..., description="Target chain ID (501, 8453, 137, 42161)")
    reserve_usdc: float = Field(..., ge=0, description="Total vault reserve in USDC")
    reserved_in_escrow_usdc: float = Field(..., ge=0, description="USDC committed in active escrow locks")
    pending_demand_usdc: float = Field(default=0.0, ge=0, description="Incoming unfulfilled settlement demand")


class ExecuteRebalanceRequest(BaseModel):
    route_id: str
    source_chain_id: int
    source_chain_name: str
    target_chain_id: int
    target_chain_name: str
    amount_usdc: float
    bridge_protocol: str = Field(default="CIRCLE_CCTP")
    estimated_latency_seconds: float = Field(default=20.0)
    bridge_toll_usdc: float = Field(default=0.0)
    slippage_percent: float = Field(default=0.0)
    proof_hash: str
    timestamp: int


@router.get("/summary", summary="Get Global Multi-Chain Liquidity Summary")
def get_liquidity_summary() -> Dict[str, Any]:
    """Returns global TVL, chain-by-chain health factors, and rebalancing capacity."""
    return cross_rail_router.get_fleet_liquidity_summary()


@router.post("/update", summary="Update Rail Pool Reserve & Demand Telemetry")
def update_pool_telemetry(payload: PoolUpdateRequest) -> Dict[str, Any]:
    """Updates live balance state for a specific settlement rail."""
    try:
        cross_rail_router.update_pool_reserve(
            chain_id=payload.chain_id,
            reserve_usdc=payload.reserve_usdc,
            reserved_in_escrow_usdc=payload.reserved_in_escrow_usdc,
            pending_demand_usdc=payload.pending_demand_usdc,
        )
        return {
            "status": "SUCCESS",
            "message": f"Pool telemetry updated for chain {payload.chain_id}",
            "pool": cross_rail_router.pools[payload.chain_id]
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/rebalance/plan", summary="Generate Optimal Cross-Rail Rebalance Plan")
def plan_rebalance() -> Dict[str, Any]:
    """Formulates deterministic, optimal CCTP routes from surplus to deficit rails with Oracle Attestations."""
    routes = cross_rail_router.plan_rebalance_routes()
    return {
        "status": "SUCCESS",
        "route_count": len(routes),
        "routes": [
            {
                "route_id": r.route_id,
                "source_chain_id": r.source_chain_id,
                "source_chain_name": r.source_chain_name,
                "target_chain_id": r.target_chain_id,
                "target_chain_name": r.target_chain_name,
                "amount_usdc": r.amount_usdc,
                "bridge_protocol": r.bridge_protocol.value,
                "estimated_latency_seconds": r.estimated_latency_seconds,
                "bridge_toll_usdc": r.bridge_toll_usdc,
                "slippage_percent": r.slippage_percent,
                "proof_hash": r.proof_hash,
                "timestamp": r.timestamp,
            }
            for r in routes
        ]
    }


@router.post("/rebalance/execute", summary="Execute Oracle-Attested Rebalance Route")
def execute_rebalance(payload: ExecuteRebalanceRequest) -> Dict[str, Any]:
    """Verifies Oracle cryptographic signature and executes rebalance settlement."""
    try:
        protocol_enum = BridgeProtocol(payload.bridge_protocol)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported bridge protocol {payload.bridge_protocol}"
        )

    route = RebalanceRoute(
        route_id=payload.route_id,
        source_chain_id=payload.source_chain_id,
        source_chain_name=payload.source_chain_name,
        target_chain_id=payload.target_chain_id,
        target_chain_name=payload.target_chain_name,
        amount_usdc=payload.amount_usdc,
        bridge_protocol=protocol_enum,
        estimated_latency_seconds=payload.estimated_latency_seconds,
        bridge_toll_usdc=payload.bridge_toll_usdc,
        slippage_percent=payload.slippage_percent,
        proof_hash=payload.proof_hash,
        timestamp=payload.timestamp,
    )

    try:
        result = cross_rail_router.execute_rebalance(route)
        return result
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
