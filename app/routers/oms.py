"""Polygon Open Money Stack (OMS) × Solana & Multi-Chain Agentic Payments Router.

Exposes REST endpoints for:
- Regulated Fiat Pay-ins & Virtual Accounts matched to Solana/Polygon USDC.
- Team-configured Agent Spend Controls (Oct 21, 2026 specification).
- Sub-5ms Zero-Trust Pre-Sign Security & Truth Verification before single-tx routing
  across Solana (501), Polygon (137), Base (8453), Arbitrum (42161), and TRON (728126428).
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.polygon_oms_adapter import polygon_oms_solana_adapter

router = APIRouter(prefix="/api/v1/oms", tags=["Polygon OMS × Solana Agentic Payments"])


class OMSPayinRequest(BaseModel):
    owner_handle: str = Field(..., description="Agent or customer handle (e.g., maria.pol or diego.sol)")
    amount_usd: float = Field(..., gt=0, description="Fiat USD deposit amount")
    payin_method: str = Field(
        default="BANK_TRANSFER",
        description="BANK_TRANSFER, WIRE, CARD, CASH, or CRYPTO",
    )
    auto_lock_escrow: bool = Field(
        default=False,
        description="Whether to immediately lock the minted Solana/Polygon USDC into A.GRID Escrow",
    )


class OMSSpendPolicyRequest(BaseModel):
    agent_handle: str = Field(..., description="Agent handle or identifier")
    wallet_address: str = Field(..., description="Solana Base58 or EVM 0x embedded wallet address")
    max_single_tx_usdc: float = Field(default=5_000.0, gt=0)
    daily_spend_limit_usdc: float = Field(default=25_000.0, gt=0)
    allowed_chains: Optional[List[int]] = Field(
        default=None,
        description="Whitelisted chain IDs (e.g., [501, 137, 8453, 42161, 728126428])",
    )
    allowed_assets: Optional[List[str]] = Field(
        default=None,
        description="Whitelisted assets (e.g., ['USDC', 'USDT', 'PYUSD', 'SOL', 'wSOL'])",
    )
    require_security_gate_attestation: bool = Field(default=True)
    max_allowed_risk_score: float = Field(default=0.30, ge=0.0, le=1.0)


class OMSPreSignPaymentRequest(BaseModel):
    sender_handle: str = Field(default="maria.pol", description="Sender OMS handle or agent ID")
    recipient_handle: str = Field(default="diego.sol", description="Recipient OMS handle or wallet")
    amount_usd: float = Field(..., gt=0, description="Gross payment amount in USD/USDC")
    source_chain_id: int = Field(default=137, description="Origin chain ID (e.g., 137 Polygon, 501 Solana, 1 Ethereum)")
    source_asset: str = Field(default="USDC", description="Origin token (USDC, USDT, PYUSD, SOL, wSOL)")
    target_chain_id: int = Field(default=501, description="Destination chain ID (e.g., 501 Solana, 137 Polygon, 728126428 TRON)")
    target_asset: str = Field(default="USDC", description="Destination token (USDC, USDT, PYUSD, SOL, wSOL)")
    payout_type: str = Field(
        default="WALLET",
        description="WALLET, BANK_ACCOUNT, CARD, or CASH_PICKUP",
    )
    payout_fiat_currency: Optional[str] = Field(
        default=None,
        description="Optional fiat off-ramp currency (USD, MXN, EUR, GBP, KRW)",
    )
    agent_prompt_or_deliverable: str = Field(
        default="Verified milestone settlement",
        description="Agent reasoning trace, prompt, or deliverable payload to inspect before signing",
    )
    is_code_deliverable: bool = Field(default=False)
    milestones_total: int = Field(default=1, ge=1)
    milestones_done: int = Field(default=1, ge=0)
    quality_score: float = Field(default=0.98, ge=0.0, le=1.0)
    referral_agent_address: Optional[str] = Field(
        default=None,
        description="Referring agent wallet to receive 20% (2000 bps) protocol fee rebate",
    )


@router.get("/telemetry", summary="Get Polygon OMS × Solana Ecosystem Telemetry")
def get_oms_telemetry() -> Dict[str, Any]:
    """Returns active virtual accounts, spend policies, and supported cross-chain corridors."""
    return polygon_oms_solana_adapter.get_ecosystem_telemetry()


@router.post("/virtual-account/payin", summary="Process Regulated Fiat Pay-In to Solana/Polygon Account")
def process_virtual_account_payin(payload: OMSPayinRequest) -> Dict[str, Any]:
    """Matches incoming Bank Transfer, Wire, Card, or Cash deposit to a Solana/Polygon embedded wallet."""
    try:
        return polygon_oms_solana_adapter.process_fiat_payin(
            owner_handle=payload.owner_handle,
            amount_usd=payload.amount_usd,
            payin_method=payload.payin_method,
            auto_lock_escrow=payload.auto_lock_escrow,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/spend-controls", summary="Configure Polygon OMS Agent Spend Controls")
def configure_spend_controls(payload: OMSSpendPolicyRequest) -> Dict[str, Any]:
    """Sets team-defined spending limits, whitelisted chains/assets, and mandatory Security Gate checks."""
    policy = polygon_oms_solana_adapter.configure_agent_spend_policy(
        agent_handle=payload.agent_handle,
        wallet_address=payload.wallet_address,
        max_single_tx_usdc=payload.max_single_tx_usdc,
        daily_spend_limit_usdc=payload.daily_spend_limit_usdc,
        allowed_chains=payload.allowed_chains,
        allowed_assets=payload.allowed_assets,
        require_security_gate_attestation=payload.require_security_gate_attestation,
        max_allowed_risk_score=payload.max_allowed_risk_score,
    )
    return {
        "status": "CONFIGURED",
        "agent_handle": policy.agent_handle,
        "wallet_address": policy.wallet_address,
        "max_single_tx_usdc": policy.max_single_tx_usdc,
        "daily_spend_limit_usdc": policy.daily_spend_limit_usdc,
        "allowed_chains": policy.allowed_chains,
        "allowed_assets": policy.allowed_assets,
        "require_security_gate_attestation": policy.require_security_gate_attestation,
    }


@router.post("/pre-sign-check", summary="Execute <5ms Pre-Sign Security Check & Single-Tx OMS Route")
def verify_and_route_oms_payment(payload: OMSPreSignPaymentRequest) -> Dict[str, Any]:
    """Audits agent intent for prompt injection/code threats, enforces Spend Controls, and routes across Solana/EVM/Fiat."""
    try:
        return polygon_oms_solana_adapter.verify_and_orchestrate_oms_payment(
            sender_handle=payload.sender_handle,
            recipient_handle=payload.recipient_handle,
            amount_usd=payload.amount_usd,
            source_chain_id=payload.source_chain_id,
            source_asset=payload.source_asset,
            target_chain_id=payload.target_chain_id,
            target_asset=payload.target_asset,
            payout_type=payload.payout_type,
            payout_fiat_currency=payload.payout_fiat_currency,
            agent_prompt_or_deliverable=payload.agent_prompt_or_deliverable,
            is_code_deliverable=payload.is_code_deliverable,
            milestones_total=payload.milestones_total,
            milestones_done=payload.milestones_done,
            quality_score=payload.quality_score,
            referral_agent_address=payload.referral_agent_address,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

