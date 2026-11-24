"""A.GRID Counterparty KYW & Multi-Chain Solvency Oracle Router (x402 Protected)."""

from typing import Optional
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from app.kyw_solvency_oracle import get_kyw_stats, verify_counterparty_kyw
from app.routers.common import require_x402_payment

router = APIRouter(prefix="/api/v1/kyw", tags=["KYW & Solvency Oracle"])


class KywVerifyRequest(BaseModel):
    counterparty_address: str = Field(..., description="Target EVM (0x...) or Solana wallet address")
    chain_id: int = Field(default=8453, description="Chain ID: 8453 (Base), 137 (Polygon), 42161 (Arbitrum), 1 (ETH), 501 (Solana)")
    required_amount_usdc: float = Field(default=0.0, ge=0.0, description="Minimum required USDC balance for solvency check")
    escrow_job_id: Optional[str] = Field(default=None, description="Optional escrow job identifier")
    payload_to_audit: Optional[str] = Field(default=None, description="Optional prompt/code payload for combined <3ms Pre-Sign Security Gate audit")


@router.get("/stats", summary="Get KYW & Solvency Oracle telemetry and supported chains")
async def kyw_stats():
    return get_kyw_stats()


@router.post("/verify", summary="Run unified Counterparty KYW, Solvency & optional Pre-Sign Security Gate check")
async def kyw_verify(
    req: KywVerifyRequest,
    request: Request,
    auth_check=Depends(require_x402_payment),
):
    if auth_check is not None:
        return auth_check

    return verify_counterparty_kyw(
        counterparty_address=req.counterparty_address,
        chain_id=req.chain_id,
        required_amount_usdc=req.required_amount_usdc,
        escrow_job_id=req.escrow_job_id,
        payload_to_audit=req.payload_to_audit,
    )
