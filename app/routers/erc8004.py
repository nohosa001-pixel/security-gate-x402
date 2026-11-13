"""FastAPI router for Polygon ERC-8004 Identity, Reputation & Validation endpoints."""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.erc8004_registry import (
    DEFAULT_HUB_BASE_URL,
    ERC8004_DEPLOYMENTS,
    build_agrid_registration_json,
    build_register_calldata,
    build_reputation_feedback_payload,
    build_validation_response_payload,
    query_identity_onchain,
)

router = APIRouter(tags=["ERC-8004"])


class RegisterCalldataRequest(BaseModel):
    agent_uri: str = Field(
        default=f"{DEFAULT_HUB_BASE_URL}/.well-known/erc8004-registration.json",
        description="HTTPS or IPFS URI pointing to the ERC-8004 registration JSON.",
    )
    network: str = Field(default="polygon-mainnet", description="polygon-mainnet or polygon-amoy")


class ValidationRequest(BaseModel):
    payload_text: str = Field(..., min_length=1, description="Agent output or code to inspect")
    is_code: bool = Field(default=False)
    ground_truth: Optional[str] = Field(default=None)
    request_hash: Optional[str] = Field(default=None)


class ReputationProofRequest(BaseModel):
    agent_id: int = Field(..., ge=0)
    score: int = Field(..., ge=0, le=100)
    x402_tx_hash: str = Field(..., min_length=6)
    chain_id: int = Field(default=137)
    tag1: str = Field(default="x402-settlement")
    tag2: str = Field(default="security-gate-passed")


@router.get("/.well-known/erc8004-registration.json")
@router.get("/api/v1/erc8004/registration.json")
def get_erc8004_registration(
    agent_id: Optional[int] = Query(default=None, ge=0),
) -> Dict[str, Any]:
    """Serve A.GRID's canonical ERC-8004 agent registration JSON."""
    return build_agrid_registration_json(agent_id=agent_id)


@router.get("/api/v1/erc8004/deployments")
def get_erc8004_deployments() -> Dict[str, Any]:
    """Return official Polygon Mainnet & Amoy ERC-8004 singleton registry addresses."""
    return {"deployments": ERC8004_DEPLOYMENTS}


@router.post("/api/v1/erc8004/register-calldata")
def create_register_calldata(req: RegisterCalldataRequest) -> Dict[str, Any]:
    """Build unsigned IdentityRegistry.register(agentURI) transaction calldata."""
    try:
        return build_register_calldata(agent_uri=req.agent_uri, network=req.network)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/v1/erc8004/validate")
def validate_for_erc8004(req: ValidationRequest) -> Dict[str, Any]:
    """Inspect payload with A.GRID <5ms Security Gate and return ERC-8004 validation payload."""
    return build_validation_response_payload(
        payload_text=req.payload_text,
        is_code=req.is_code,
        ground_truth=req.ground_truth,
        request_hash=req.request_hash,
    )


@router.post("/api/v1/erc8004/reputation-proof")
def create_reputation_proof(req: ReputationProofRequest) -> Dict[str, Any]:
    """Generate an ERC-8004 ReputationRegistry feedback payload linked to an x402 proof."""
    try:
        return build_reputation_feedback_payload(
            agent_id=req.agent_id,
            score=req.score,
            x402_tx_hash=req.x402_tx_hash,
            chain_id=req.chain_id,
            tag1=req.tag1,
            tag2=req.tag2,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/api/v1/erc8004/agent/{agent_id}")
def lookup_erc8004_agent(
    agent_id: int,
    network: str = Query(default="polygon-mainnet"),
) -> Dict[str, Any]:
    """Read-only lookup of an agentId on Polygon Mainnet or Amoy IdentityRegistry."""
    try:
        return query_identity_onchain(agent_id=agent_id, network=network)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"On-chain lookup failed: {exc}") from exc

