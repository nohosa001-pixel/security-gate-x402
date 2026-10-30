"""Autonomous Cross-Rail Liquidity Router for agent-security-gate-x402 (Phase 2).

Orchestrates autonomous liquidity rebalancing between high-frequency execution rails:
- Solana Mainnet (Chain ID 501, 0.4s finality micro-streaming)
- EVM Settlement Rails:
  - Base Mainnet (Chain ID 8453, Coinbase Smart Wallet & AgentKit)
  - Polygon Mainnet (Chain ID 137, OMS Smart Sessions)
  - Arbitrum One (Chain ID 42161, Safe{Wallet} Treasury Guard & Stylus)

Core Invariants:
1. Zero-Slippage Bridging: Prioritizes Circle CCTP (Cross-Chain Transfer Protocol) native 1:1 mint/burn.
2. Deficit Protection: Automatically detects liquidity depletion on fast streaming rails (Solana) and rebalances from surplus EVM vaults.
3. Cryptographic Guard: Requires EIP-712/SHA-256 Oracle Attestation before executing any cross-chain pool transfer.
4. Risk Ceiling: Enforces Single Rebalance Cap ($50,000 USDC) and 24h Cumulative Cap ($250,000 USDC).
"""

from __future__ import annotations

import hashlib
import hmac
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class BridgeProtocol(str, Enum):
    CIRCLE_CCTP = "CIRCLE_CCTP"              # Native 1:1 burn & mint, 0% slippage
    DLN_INTENT = "DLN_INTENT"                # Sub-second cross-chain intent filler
    WORMHOLE_CORE = "WORMHOLE_CORE"          # Cross-chain governance message layer
    POLYGON_OMS = "POLYGON_OMS"              # Polygon Open Money Stack (OMS) Native Solana-EVM Route (Oct 29, 2026)


@dataclass
class ChainLiquidityPool:
    chain_id: int
    name: str
    symbol: str
    reserve_usdc: float                      # Available USDC in Vault
    reserved_in_escrow_usdc: float           # Committed in active escrows
    target_weight_percent: float             # Optimal target share of global liquidity (e.g., 40%)
    pending_demand_usdc: float = 0.0         # Incoming unfulfilled agent settlement demand
    min_reserve_threshold_usdc: float = 5_000.0  # Safe minimum floor

    @property
    def free_liquidity_usdc(self) -> float:
        return max(0.0, self.reserve_usdc - self.reserved_in_escrow_usdc)


@dataclass
class RebalanceRoute:
    route_id: str
    source_chain_id: int
    source_chain_name: str
    target_chain_id: int
    target_chain_name: str
    amount_usdc: float
    bridge_protocol: BridgeProtocol
    estimated_latency_seconds: float
    bridge_toll_usdc: float
    slippage_percent: float
    proof_hash: str
    timestamp: int


class AutonomousCrossRailRouter:
    """Manages real-time cross-rail liquidity equilibrium across Solana and EVM chains."""

    # Default Target Portfolio Allocation
    DEFAULT_WEIGHTS: Dict[int, float] = {
        501: 35.0,    # Solana Mainnet (35% - High-velocity micro-streaming)
        8453: 30.0,   # Base Mainnet (30% - Coinbase AgentKit transactions)
        137: 20.0,    # Polygon Mainnet (20% - OMS Enterprise sessions)
        42161: 15.0,  # Arbitrum One (15% - Safe{Wallet} Treasury buffer)
    }

    # Safety Invariants
    IMBALANCE_TOLERANCE_PERCENT = 10.0       # Trigger rebalance if deviation exceeds 10%
    SINGLE_REBALANCE_CAP_USDC = 50_000.0     # Max $50k per rebalance tx
    MIN_REBALANCE_AMOUNT_USDC = 500.0        # Avoid micro dust rebalancing
    DAILY_REBALANCE_LIMIT_USDC = 250_000.0   # $250k daily velocity ceiling

    # Protocol Toll for CCTP and Relay
    CCTP_PROTOCOL_TOLL_BPS = 5               # 0.05% flat bridge toll for relayer gas
    DLN_INTENT_TOLL_BPS = 12                 # 0.12% for ultra-fast intent fillers
    POLYGON_OMS_TOLL_BPS = 3                 # 0.03% regulated OMS protocol toll for Solana-Polygon route

    def __init__(
        self,
        oracle_signing_key: Optional[str] = None,
        custom_weights: Optional[Dict[int, float]] = None
    ) -> None:
        self.oracle_key = (oracle_signing_key or "agrid_cross_rail_oracle_master_secret").encode("utf-8")
        self.weights = custom_weights or self.DEFAULT_WEIGHTS.copy()
        self.pools: Dict[int, ChainLiquidityPool] = {}
        self.cumulative_24h_rebalance_usdc: float = 0.0
        self.last_rebalance_reset_time: float = time.time()
        self.rebalance_history: List[RebalanceRoute] = []

        # Initialize default mock state pools
        self._initialize_default_pools()

    def _initialize_default_pools(self) -> None:
        """Initializes baseline liquidity pools across the 4 major chains."""
        self.pools = {
            501: ChainLiquidityPool(
                chain_id=501,
                name="Solana Mainnet",
                symbol="SOL",
                reserve_usdc=45_000.0,
                reserved_in_escrow_usdc=30_000.0,  # High utilization
                target_weight_percent=self.weights.get(501, 35.0),
                pending_demand_usdc=25_000.0       # High pending demand -> Deficit candidate
            ),
            8453: ChainLiquidityPool(
                chain_id=8453,
                name="Base Mainnet",
                symbol="BASE",
                reserve_usdc=110_000.0,
                reserved_in_escrow_usdc=20_000.0,  # High free reserve -> Surplus candidate
                target_weight_percent=self.weights.get(8453, 30.0),
                pending_demand_usdc=5_000.0
            ),
            137: ChainLiquidityPool(
                chain_id=137,
                name="Polygon Mainnet",
                symbol="POL",
                reserve_usdc=60_000.0,
                reserved_in_escrow_usdc=15_000.0,
                target_weight_percent=self.weights.get(137, 20.0),
                pending_demand_usdc=2_000.0
            ),
            42161: ChainLiquidityPool(
                chain_id=42161,
                name="Arbitrum One",
                symbol="ARB",
                reserve_usdc=35_000.0,
                reserved_in_escrow_usdc=10_000.0,
                target_weight_percent=self.weights.get(42161, 15.0),
                pending_demand_usdc=1_000.0
            )
        }

    def update_pool_reserve(
        self,
        chain_id: int,
        reserve_usdc: float,
        reserved_in_escrow_usdc: float,
        pending_demand_usdc: float = 0.0
    ) -> None:
        """Updates live on-chain balances for a specific settlement rail."""
        if chain_id not in self.pools:
            raise ValueError(f"Unsupported chain_id {chain_id}")
        pool = self.pools[chain_id]
        pool.reserve_usdc = reserve_usdc
        pool.reserved_in_escrow_usdc = reserved_in_escrow_usdc
        pool.pending_demand_usdc = pending_demand_usdc

    def get_fleet_liquidity_summary(self) -> Dict[str, Any]:
        """Calculates global TVL, chain-by-chain health factors, and deviations."""
        total_reserve = sum(p.reserve_usdc for p in self.pools.values())
        total_free = sum(p.free_liquidity_usdc for p in self.pools.values())
        total_pending_demand = sum(p.pending_demand_usdc for p in self.pools.values())

        chain_analysis: Dict[int, Dict[str, Any]] = {}
        for cid, pool in self.pools.items():
            current_share = (pool.reserve_usdc / total_reserve * 100.0) if total_reserve > 0 else 0.0
            deviation = current_share - pool.target_weight_percent
            # Health factor: Free liquidity relative to pending demand & safety floor
            net_need = max(pool.pending_demand_usdc, pool.min_reserve_threshold_usdc)
            health_factor = (pool.free_liquidity_usdc / net_need) if net_need > 0 else 2.0

            chain_analysis[cid] = {
                "chain_id": cid,
                "name": pool.name,
                "reserve_usdc": pool.reserve_usdc,
                "free_liquidity_usdc": pool.free_liquidity_usdc,
                "pending_demand_usdc": pool.pending_demand_usdc,
                "target_weight_percent": pool.target_weight_percent,
                "current_share_percent": round(current_share, 2),
                "weight_deviation_percent": round(deviation, 2),
                "health_factor": round(health_factor, 2),
                "status": "DEFICIT" if health_factor < 1.0 or deviation < -self.IMBALANCE_TOLERANCE_PERCENT else (
                    "SURPLUS" if deviation > self.IMBALANCE_TOLERANCE_PERCENT else "BALANCED"
                )
            }

        return {
            "total_reserve_usdc": total_reserve,
            "total_free_liquidity_usdc": total_free,
            "total_pending_demand_usdc": total_pending_demand,
            "24h_rebalance_volume_usdc": self.cumulative_24h_rebalance_usdc,
            "24h_rebalance_capacity_remaining_usdc": max(0.0, self.DAILY_REBALANCE_LIMIT_USDC - self.cumulative_24h_rebalance_usdc),
            "chains": chain_analysis
        }

    def detect_imbalances(self) -> Tuple[List[ChainLiquidityPool], List[ChainLiquidityPool]]:
        """Identifies deficit pools (needing capital) and surplus pools (excess capital)."""
        summary = self.get_fleet_liquidity_summary()
        deficit_pools: List[ChainLiquidityPool] = []
        surplus_pools: List[ChainLiquidityPool] = []

        for cid, data in summary["chains"].items():
            pool = self.pools[cid]
            if data["status"] == "DEFICIT":
                deficit_pools.append(pool)
            elif data["status"] == "SURPLUS":
                surplus_pools.append(pool)

        return deficit_pools, surplus_pools

    def plan_rebalance_routes(self) -> List[RebalanceRoute]:
        """Formulates deterministic, optimal rebalancing routes from surplus to deficit rails."""
        deficit_pools, surplus_pools = self.detect_imbalances()
        if not deficit_pools or not surplus_pools:
            return []

        routes: List[RebalanceRoute] = []
        now = int(time.time())

        # Sort deficits by severity (most urgent first: lowest free liquidity vs demand)
        deficit_pools.sort(key=lambda p: (p.free_liquidity_usdc - p.pending_demand_usdc))
        # Sort surplus by largest available free liquidity
        surplus_pools.sort(key=lambda p: p.free_liquidity_usdc, reverse=True)

        # Track surplus availability locally during route planning
        surplus_available: Dict[int, float] = {
            s.chain_id: max(0.0, s.free_liquidity_usdc - s.min_reserve_threshold_usdc)
            for s in surplus_pools
        }

        for deficit in deficit_pools:
            needed_usdc = max(
                deficit.pending_demand_usdc - deficit.free_liquidity_usdc + deficit.min_reserve_threshold_usdc,
                self.MIN_REBALANCE_AMOUNT_USDC
            )

            for surplus in surplus_pools:
                if needed_usdc <= 0:
                    break

                avail = surplus_available.get(surplus.chain_id, 0.0)
                if avail < self.MIN_REBALANCE_AMOUNT_USDC:
                    continue

                transfer_amount = min(needed_usdc, avail, self.SINGLE_REBALANCE_CAP_USDC)
                # Check remaining 24h cap
                remaining_cap = self.DAILY_REBALANCE_LIMIT_USDC - self.cumulative_24h_rebalance_usdc
                transfer_amount = min(transfer_amount, remaining_cap)

                if transfer_amount < self.MIN_REBALANCE_AMOUNT_USDC:
                    continue

                # Choose optimal bridge protocol
                # If bridging between Solana (501) and EVM rails:
                is_cross_svm_evm = (deficit.chain_id == 501 or surplus.chain_id == 501)
                is_polygon_involved = (deficit.chain_id == 137 or surplus.chain_id == 137)

                if is_cross_svm_evm and is_polygon_involved:
                    # Polygon Open Money Stack (OMS) Solana Native Rail (Launched Oct 29, 2026)
                    # Regulated single-transaction routing between Polygon and Solana
                    protocol = BridgeProtocol.POLYGON_OMS
                    latency = 1.2  # Sub-2-second OMS atomic routing
                    toll = transfer_amount * (self.POLYGON_OMS_TOLL_BPS / 10000.0)
                elif is_cross_svm_evm:
                    protocol = BridgeProtocol.CIRCLE_CCTP
                    latency = 20.0  # ~20s CCTP attestation finality
                    toll = transfer_amount * (self.CCTP_PROTOCOL_TOLL_BPS / 10000.0)
                else:
                    # EVM to EVM (e.g. Base to Arbitrum)
                    protocol = BridgeProtocol.CIRCLE_CCTP
                    latency = 12.0
                    toll = transfer_amount * (self.CCTP_PROTOCOL_TOLL_BPS / 10000.0)

                # Generate cryptographic proof hash
                proof_payload = f"{surplus.chain_id}->{deficit.chain_id}:{transfer_amount}:{protocol.value}:{now}"
                proof_hash = hmac.new(self.oracle_key, proof_payload.encode("utf-8"), hashlib.sha256).hexdigest()

                route = RebalanceRoute(
                    route_id=f"REBAL-{surplus.chain_id}-{deficit.chain_id}-{now}",
                    source_chain_id=surplus.chain_id,
                    source_chain_name=surplus.name,
                    target_chain_id=deficit.chain_id,
                    target_chain_name=deficit.name,
                    amount_usdc=round(transfer_amount, 2),
                    bridge_protocol=protocol,
                    estimated_latency_seconds=latency,
                    bridge_toll_usdc=round(toll, 4),
                    slippage_percent=0.0,  # CCTP has zero slippage
                    proof_hash=proof_hash,
                    timestamp=now
                )

                routes.append(route)
                needed_usdc -= transfer_amount
                surplus_available[surplus.chain_id] -= transfer_amount

        return routes

    def verify_rebalance_attestation(self, route: RebalanceRoute) -> bool:
        """Verifies the cryptographic HMAC/SHA-256 Oracle Attestation on the rebalance route."""
        expected_payload = f"{route.source_chain_id}->{route.target_chain_id}:{route.amount_usdc}:{route.bridge_protocol.value}:{route.timestamp}"
        expected_hash = hmac.new(self.oracle_key, expected_payload.encode("utf-8"), hashlib.sha256).hexdigest()
        return hmac.compare_digest(route.proof_hash, expected_hash)

    def execute_rebalance(self, route: RebalanceRoute) -> Dict[str, Any]:
        """Validates and executes an approved cross-rail rebalancing route."""
        # 1. Attestation Check
        if not self.verify_rebalance_attestation(route):
            raise PermissionError("Invalid or tampered rebalance oracle attestation")

        # 2. Invariant Check: Single Tx Cap
        if route.amount_usdc > self.SINGLE_REBALANCE_CAP_USDC:
            raise ValueError(f"Rebalance amount {route.amount_usdc} exceeds single tx cap of {self.SINGLE_REBALANCE_CAP_USDC}")

        # 3. Invariant Check: 24h Cap
        if (self.cumulative_24h_rebalance_usdc + route.amount_usdc) > self.DAILY_REBALANCE_LIMIT_USDC:
            raise ValueError(f"Rebalance would breach 24h cumulative limit of {self.DAILY_REBALANCE_LIMIT_USDC}")

        # 4. Source and Target Pool Update
        source = self.pools[route.source_chain_id]
        target = self.pools[route.target_chain_id]

        source.reserve_usdc -= route.amount_usdc
        net_received = route.amount_usdc - route.bridge_toll_usdc
        target.reserve_usdc += net_received
        # Deduct pending demand fulfilled on target
        target.pending_demand_usdc = max(0.0, target.pending_demand_usdc - net_received)

        self.cumulative_24h_rebalance_usdc += route.amount_usdc
        self.rebalance_history.append(route)

        return {
            "status": "SETTLED",
            "route_id": route.route_id,
            "source_chain": route.source_chain_name,
            "target_chain": route.target_chain_name,
            "amount_dispatched_usdc": route.amount_usdc,
            "net_received_usdc": round(net_received, 2),
            "bridge_protocol": route.bridge_protocol.value,
            "toll_paid_usdc": route.bridge_toll_usdc,
            "proof_hash": route.proof_hash,
            "new_source_reserve": round(source.reserve_usdc, 2),
            "new_target_reserve": round(target.reserve_usdc, 2)
        }
