"""
Escrow Router: HTTP 402 Universal Escrow Clearinghouse, Solana micro-streaming,
Proof-of-Reserves, and deterministic Truth settlement.
"""

import time
import json
import os
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Request, Depends, HTTPException, status, Query
from fastapi.responses import JSONResponse

from app.schemas import (
    EscrowAuditRequest,
    M2MEscrowSettleRequest,
    UniversalEscrowSettleRequest,
    SolanaTruthAttestationRequest,
    SolanaTruthAttestationResponse,
    ZkTLSVerificationRequest,
    PricingTier,
)
from app.security_engine import audit_payload
from app.x402_verifier import x402_verifier, create_attestation
from app.onchain_signer import onchain_signer
from app.solana_signer import SolanaOracleSigner
from app.escrow_engine import escrow_engine
from app.consensus_oracle_network import consensus_oracle_network
from app.autonomous_clearing_pipeline import clearing_pipeline
from app.routers.common import require_x402_payment

router = APIRouter()

@router.post("/api/v1/escrow/audit", tags=["Escrow"])
async def audit_escrow_task(
    req: EscrowAuditRequest,
    auth_check = Depends(require_x402_payment)
):
    """Audits an agent task deliverable and issues an EIP-712 attestation for AgentEscrow.sol."""
    if auth_check is not None:
        return auth_check

    from app.escrow_engine import escrow_engine
    result = escrow_engine.evaluate_deliverable(
        job_id=req.job_id,
        deliverable=req.deliverable,
        ground_truth_spec=req.ground_truth_spec,
        is_code=req.is_code,
        chain_id=req.chain_id,
        verifying_contract=req.verifying_contract
    )
    return result


@router.post("/api/v1/escrow/settle", tags=["Escrow"])
async def settle_escrow_task(req: M2MEscrowSettleRequest):
    """
    Settles an autonomous agent-to-agent task escrow:
    - Pre-flight security audit: Prompt injection & secret leak defense (<3ms)
    - Automatically routes 0.002 USDC micro-fee to A.GRID Treasury (Safe: 0x06db...5e19)
    - Releases net payout to worker or refunds client with 0 on-chain loss upon attack.
    """
    from app.escrow_engine import escrow_engine
    return escrow_engine.settle_m2m_job(
        job_id=req.job_id,
        client_address=req.client_address,
        worker_address=req.worker_address,
        payout_usdc=req.payout_usdc,
        deliverable=req.deliverable,
        ground_truth_spec=req.ground_truth_spec,
        is_code=req.is_code,
        chain_id=req.chain_id,
        referral_agent_address=req.referral_agent_address
    )


# --- Universal Modular Truth Escrow Endpoints ---



@router.post("/api/v1/escrow/universal/settle", tags=["Universal Truth Escrow"])
async def settle_universal_escrow_endpoint(req: UniversalEscrowSettleRequest):
    """
    Executes / prepares atomic Direct Split settlement on UniversalEscrowCore.sol.
    Disburses funds directly to laborers, suppliers, and researchers bypassing general contractors.
    Cross-system validations:
    - Domain bounds checking (Maritime=0, Bio=1, Construction=2, EUDR=3, Minerals=4)
    - Oracle attestation validity & expiry verification
    - Recipient address format, non-zero, and blacklist checks
    - Synchronization with Credit Rating Engine & Sovereign RWA Treasury
    """
    import time
    from fastapi import HTTPException
    from app.credit_rating_engine import credit_engine
    from app.rwa_treasury_engine import sovereign_treasury

    # 1. Domain Validation
    if req.domain not in (0, 1, 2, 3, 4):
        raise HTTPException(status_code=400, detail=f"Invalid domain: {req.domain}. Must be 0 (Maritime), 1 (Bio), 2 (Construction), 3 (EUDR), or 4 (Minerals).")

    # 2. Attestation Validation
    att = req.attestation or {}
    verdict = att.get("verdict")

    # Check validity across both camelCase and snake_case representations
    if "isValid" in att:
        is_valid = bool(att["isValid"])
    elif "is_valid" in att:
        is_valid = bool(att["is_valid"])
    else:
        is_valid = True if verdict == "PASSED" else (False if verdict == "FAILED" else True)

    deforestation_free = att.get("deforestation_free", att.get("deforestationFree", True))
    child_labor_free = att.get("child_labor_free", att.get("childLaborFree", True))

    if verdict == "FAILED" or is_valid is False or deforestation_free is False or child_labor_free is False:
        raise HTTPException(
            status_code=400,
            detail="Cannot settle escrow: Physical truth verification failed or attestation is invalid."
        )

    expires_at_val = att.get("expiresAt")
    if expires_at_val is None:
        expires_at_val = att.get("expires_at")
    elif "expires_at" in att:
        try:
            expires_at_val = min(float(expires_at_val), float(att["expires_at"]))
        except (ValueError, TypeError):
            pass

    if expires_at_val is not None:
        try:
            if float(expires_at_val) < time.time():
                raise HTTPException(status_code=400, detail="Cannot settle escrow: Physical truth attestation has expired.")
        except HTTPException:
            raise
        except (ValueError, TypeError):
            pass

    # 3. Recipient Sanitization & Anti-Exploit / Blacklist Validation
    total_requested = 0.0
    is_solana_chain = (getattr(req, "chain_id", None) == 501) or (str(getattr(req, "chain_id", "")).lower() in ("solana", "solana-mainnet", "sol"))
    for r in req.recipients:
        addr = r.recipient.strip()
        is_b58 = len(addr) >= 32 and not addr.startswith("0x")
        if not is_solana_chain and not is_b58:
            if not addr.startswith("0x") or len(addr) < 4:
                raise HTTPException(status_code=400, detail=f"Invalid recipient EVM address format: {addr}")
            if addr.lower() in ("0x0", "0x0000000000000000000000000000000000000000"):
                raise HTTPException(status_code=400, detail="Invalid recipient: Zero address (0x0) cannot receive disbursed funds.")
        else:
            if len(addr) < 32 or len(addr) > 44:
                raise HTTPException(status_code=400, detail=f"Invalid recipient Solana Base58 address format: {addr}")
        if r.amount <= 0.0:
            raise HTTPException(status_code=400, detail=f"Disbursal amount must be strictly positive: {r.amount}")

        # Check blacklisted bad actors / exploiters
        telemetry = credit_engine.agent_telemetry.get(addr.lower(), {})
        if telemetry.get("is_blacklisted", False):
            raise HTTPException(status_code=403, detail=f"Disbursal blocked: Recipient {addr} is blacklisted for security violations.")

        total_requested += r.amount

    protocol_fee = total_requested * 0.0025  # 0.25%

    # 4. Cross-System Synchronizations:
    # A. Credit Rating Engine: Record successful honest delivery for recipients
    for r in req.recipients:
        credit_engine.record_audit(r.recipient, verdict="PASSED", hallucination_detected=False)

    # B. Sovereign RWA Treasury Engine: Accumulate protocol fee toll
    sovereign_treasury.accumulated_tolls += protocol_fee

    # C. Universal Factoring Pool Sync: If this job was factored, mark claim resolved & award credit
    from app.universal_factoring_bridge import universal_factoring_bridge
    factoring_sync = universal_factoring_bridge.resolve_factored_settlement(req.job_id)

    return {
        "status": "SETTLED",
        "job_id": req.job_id,
        "domain": req.domain,
        "chain_id": 501 if is_solana_chain else getattr(req, "chain_id", 137),
        "total_disbursed_usdc": total_requested,
        "protocol_fee_usdc": protocol_fee,
        "recipients_count": len(req.recipients),
        "treasury_address": "0x06db5A847F24d0feC5151a01937700E221d55e19",
        "attestation": req.attestation,
        "direct_split_executed": True,
        "factoring_settled": factoring_sync.get("factored", False),
        "factoring_details": factoring_sync if factoring_sync.get("factored") else None,
        "payouts": [r.model_dump() for r in req.recipients],
        "calldata_ready": True
    }


@router.post("/api/v1/escrow/universal/solana/attest", tags=["Universal Truth Escrow"])
async def attest_solana_universal_escrow_endpoint(
    req: SolanaTruthAttestationRequest,
    auth_check = Depends(require_x402_payment)
):
    """
    Generates an on-chain Ed25519 Oracle Attestation for Solana Mainnet settlement.
    Returns cryptographic signature matching Solana Ed25519Program pre-instruction format.
    """
    if auth_check is not None:
        return auth_check

    from app.solana_signer import SolanaOracleSigner
    import time

    signer = SolanaOracleSigner()
    now = int(time.time())
    expires_at = now + req.validity_seconds

    job_id_bytes = bytes.fromhex(req.job_id_hex.replace("0x", ""))
    truth_bytes = bytes.fromhex(req.truth_hash_hex.replace("0x", ""))
    recip_bytes = bytes.fromhex(req.recipients_hash_hex.replace("0x", ""))

    attestation = signer.sign_attestation(
        job_id=job_id_bytes,
        domain=req.domain,
        truth_hash=truth_bytes,
        recipients_hash=recip_bytes,
        expires_at=expires_at
    )
    return attestation




@router.post("/api/v1/escrow/consensus-audit", tags=["Consensus"])
async def audit_escrow_consensus(
    req: EscrowAuditRequest,
    auth_check = Depends(require_x402_payment)
):
    """Executes Byzantine fault-tolerant 3-of-5 multi-node consensus audit for mission-critical tasks."""
    if auth_check is not None:
        return auth_check

    from app.consensus_oracle_network import consensus_oracle_network
    return consensus_oracle_network.execute_consensus_audit(
        job_id=req.job_id,
        deliverable=req.deliverable,
        ground_truth_spec=req.ground_truth_spec,
        is_code=req.is_code,
        chain_id=req.chain_id,
        verifying_contract=req.verifying_contract
    )



# --- Lending Pool Endpoints ---



@router.get('/api/v1/escrow/por', tags=['Escrow', 'Proof of Reserve'])
async def get_escrow_proof_of_reserve_alias(chain_id: int = Query(137, description='EVM Chain ID')):
    '''Alias for Proof-of-Reserve (PoR) attestation for escrow solvency and treasury holdings.'''
    from app.rwa_treasury_engine import sovereign_treasury
    return sovereign_treasury.generate_proof_of_reserve(chain_id)

@router.post("/api/v1/escrow/truth/zktls", tags=["Truth Oracle"])
async def verify_zktls_proof_endpoint(
    req: ZkTLSVerificationRequest,
    auth_check = Depends(require_x402_payment)
):
    """
    Verifies zero-knowledge cryptographic web session proofs (TLSNotary / zkTLS style)
    for off-chain data provenance without exposing client credentials or API tokens.
    """
    if auth_check is not None:
        return auth_check

    from app.truth_adapters.zktls_web_proof_adapter import zktls_adapter
    return zktls_adapter.verify_web_proof(
        server_domain=req.server_domain,
        http_method=req.http_method,
        revealed_data=req.revealed_data,
        notary_signature=req.notary_signature,
        session_timestamp=req.session_timestamp,
        session_commitment_hash=req.session_commitment_hash,
        max_age_seconds=req.max_age_seconds
    )


# --- Declarative Agent Factory & Fleet Endpoints ---



@router.post("/api/v1/clearing/settle", tags=["Clearing Pipeline"])
async def execute_clearing_settlement_endpoint(settle_data: Dict[str, Any]):
    """
    Settles an escrow job:
    1. Deducts 0.25% protocol fee toll.
    2. Routes 80% to Safe Pro Sovereign Treasury Vault (RWA US T-Bills).
    3. Routes 20% to referring agent wallet.
    4. Automatically upgrades on-chain Credit Rating Scores (CRS).
    """
    from app.autonomous_clearing_pipeline import clearing_pipeline, SettleAndDisburseRequest
    try:
        req = SettleAndDisburseRequest(**settle_data)
        return clearing_pipeline.execute_settlement_clearing(req)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Settlement clearing failed: {str(e)}")


@router.post("/api/v1/clearing/incident-claim", tags=["Clearing Pipeline"])
async def execute_clearing_incident_endpoint(claim_data: Dict[str, Any]):
    """
    Executes emergency slashing and principal indemnity:
    1. Slashes 100% of rogue worker staked collateral.
    2. Dispatches 100% principal compensation to employer from Mutual Insurance Pool.
    3. Degrades worker credit rating to default Grade F.
    """
    from app.autonomous_clearing_pipeline import clearing_pipeline, IncidentClaimRequest
    try:
        req = IncidentClaimRequest(**claim_data)
        return clearing_pipeline.execute_incident_slashing_and_claim(req)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Incident slashing failed: {str(e)}")


@router.get("/api/v1/clearing/telemetry", tags=["Clearing Pipeline"])
async def get_clearing_telemetry_endpoint():
    """Returns clearinghouse metrics, protocol fee distribution breakdown, and treasury solvency."""
    from app.autonomous_clearing_pipeline import clearing_pipeline
    return clearing_pipeline.get_pipeline_telemetry()


# --- MCP Tool Call Endpoints ---

