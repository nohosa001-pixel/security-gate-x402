"""
Core Gate Router: Ultra-low latency (<5ms) deterministic AST inspection,
prompt injection defense, on-chain EIP-191/712 attestations, and multi-chain configurations.
"""

import time
import os
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from app.schemas import (
    InspectionRequest,
    InspectionResponse,
    AuditReport,
    AuditAttestation,
    AuditProof,
    NLIReport,
    PricingTier,
    BatchInspectionRequest,
    BatchInspectionResponse,
    OnChainAttestationRequest,
    OnChainAttestationResponse,
    ShellInspectionRequest,
)
from app.security_engine import audit_payload, parse_code_ast
from app.x402_verifier import x402_verifier, create_attestation, generate_audit_proof
from app.onchain_signer import onchain_signer
from app.vault_manager import vault_manager
from app.credit_rating_engine import credit_engine
from app.multi_chain import list_all_chains, get_chain_info
from app.shell_security_engine import shell_security_engine
from app.routers.common import (
    require_x402_payment,
    _record_audit_telemetry,
    _recent_audit_events,
    _quarantined_ips,
)

router = APIRouter()

@router.post("/inspect", response_model=InspectionResponse, tags=["Security Gate"])
@router.post("/api/v1/inspect", response_model=InspectionResponse, tags=["Security Gate"])
@router.post("/api/v1/gate/inspect", response_model=InspectionResponse, tags=["Security Gate"])
async def inspect_payload(
    req: InspectionRequest,
    request: Request,
    auth_check = Depends(require_x402_payment)
):
    if auth_check is not None:
        return auth_check

    start_t = time.perf_counter()
    issued_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    # 1. Deterministic Security & NLI Audit
    audit = audit_payload(
        text=req.agent_output,
        is_code=req.is_code,
        ground_truth=req.context_ground_truth
    )

    # 2. Cryptographic Proof-of-Safety Attestation
    attestation_dict = create_attestation(
        agent_output=req.agent_output,
        verdict=audit.verdict,
        risk_score=audit.risk_score,
        issued_at=issued_at
    )
    attestation = AuditAttestation(**attestation_dict)

    elapsed_ms = (time.perf_counter() - start_t) * 1000.0

    # 3. Formulate payment receipt & metadata
    payer_info = getattr(request.state, "authorized_payer", "sandbox:free_trial")
    extra_headers = getattr(request.state, "extra_headers", {})
    payment_receipt = {
        "payer": payer_info,
        "protocol": "x402",
        "network": "Polygon Mainnet (137)",
        "cost_settled_usdc": "0.002",
        "latency_ms": round(elapsed_ms, 2),
        "tier": extra_headers.get("X-Tier", "STANDARD")
    }

    # Resolve agent caller address for attribution & audit proof
    agent_addr = None
    if isinstance(payer_info, str) and payer_info.startswith("0x"):
        agent_addr = payer_info
    else:
        hdr_addr = request.headers.get("x-client-address")
        if hdr_addr and hdr_addr.startswith("0x"):
            agent_addr = hdr_addr
        elif getattr(req, "client_address", None) and str(getattr(req, "client_address")).startswith("0x"):
            agent_addr = str(getattr(req, "client_address"))

    # 4. Formulate Zero-Liability Audit Proof & cryptographic provenance seal
    caller_ref = agent_addr if agent_addr else (payer_info if isinstance(payer_info, str) else "anonymous")
    audit_proof_dict = generate_audit_proof(
        payload_text=req.agent_output,
        verdict=audit.verdict,
        risk_score=audit.risk_score,
        caller_address=caller_ref if caller_ref.startswith("0x") else None,
        tx_or_payment_ref=str(payer_info)
    )
    audit_proof = AuditProof(
        proof_hash=audit_proof_dict["proof_hash"],
        signature=audit_proof_dict["signature"],
        issuer=audit_proof_dict["issuer"],
        terms=audit_proof_dict["terms"],
        timestamp=audit_proof_dict["timestamp"],
        audit_record=audit_proof_dict["audit_record"]
    )

    # 5. Record recent audit event and Prometheus telemetry
    client_ip = request.client.host if request.client else "127.0.0.1"
    masked_ip = ".".join(client_ip.split(".")[:2]) + ".*.*" if "." in client_ip else "masked"
    is_hal = audit.nli_verification.hallucination_score > 0.3 if audit.nli_verification else False
    _record_audit_telemetry(
        verdict=audit.verdict,
        risk_score=audit.risk_score,
        threats=audit.threats,
        elapsed_sec=(time.perf_counter() - start_t),
        masked_ip=masked_ip,
        is_hallucinated=is_hal
    )

    # 6. Record telemetry for agent credit rating oracle & Counter-Slashing (Economic Disaster Protocol)
    slashed_penalty_usdc = 0.0
    is_severe_exploit = audit.verdict == "BLOCKED" and (
        audit.risk_score >= 0.85
        or any("Injection" in str(t) or "AST" in str(t) or "System" in str(t) or "Malicious" in str(t) or "Exfiltration" in str(t) or "Reverse" in str(t) or "Destructive" in str(t) for t in audit.threats)
    )

    if is_severe_exploit:
        vault_k = request.headers.get("x-vault-key") or request.headers.get("X-Vault-Key")
        caller_identity = vault_k or agent_addr or request.headers.get("x-client-address") or request.headers.get("X-Client-Address")
        if caller_identity and not str(caller_identity).startswith("vault_key_security_demo_agent"):
            slashed_ok, slashed_amount, _ = vault_manager.slash_collateral(
                str(caller_identity),
                penalty_usdc=5.0,
                reason=f"Severe adversarial exploit probe: {', '.join([str(t) for t in audit.threats[:2]])}"
            )
            if slashed_ok and slashed_amount > 0:
                slashed_penalty_usdc = slashed_amount
                payment_receipt["adversarial_penalty_slashed_usdc"] = slashed_amount

        # Crush Credit Rating to Grade F (300) Defaulter / Permanent Blacklist
        target_agent = agent_addr or request.headers.get("x-client-address") or request.headers.get("X-Client-Address")
        demo_agent = "0x70997970c51812dc3a010c7d01b50e0d17dc79c8"
        if target_agent and target_agent != "anonymous" and str(target_agent).lower() != demo_agent and not str(caller_identity).startswith("vault_key_security_demo_agent"):
            credit_engine.record_exploit_attempt(
                target_agent,
                reason=f"Severe adversarial exploit probe: {', '.join([str(t) for t in audit.threats[:2]])}"
            )

        # Active Defense Quarantine: Put attacker IP in 1-hour jail unless in unit test environment
        if client_ip not in ("127.0.0.1", "testclient", "testserver") and os.getenv("TESTING") != "1":
            _quarantined_ips[client_ip] = time.time() + 3600.0

        payment_receipt["economic_retaliation"] = {
            "status": "ECONOMIC_DISASTER_ACTIVATED",
            "slashed_collateral_usdc": slashed_penalty_usdc,
            "forfeited_to_treasury": "0xA185B43fDD19619f99952AAed6eabf1029bF36a1",
            "credit_rating_penalty": "GRADE_F_300_PERMANENT_DEFAULT",
            "uncollateralized_loan_limit_usdc": 0.0,
            "action": "COLLATERAL_FORFEITURE_AND_BLACKLIST"
        }
    else:
        if agent_addr:
            is_hal = audit.nli_verification.hallucination_score > 0.3 if audit.nli_verification else False
            credit_engine.record_audit(agent_addr, audit.verdict, is_hal)

    response_data = InspectionResponse(
        status="success",
        timestamp=issued_at,
        audit=audit,
        attestation=attestation,
        audit_proof=audit_proof,
        payment_receipt=payment_receipt
    )

    resp = JSONResponse(content=response_data.model_dump())
    for k, v in extra_headers.items():
        resp.headers[k] = v
    for k, v in audit_proof_dict["headers"].items():
        resp.headers[k] = v
    if slashed_penalty_usdc > 0:
        resp.headers["X-Adversarial-Penalty"] = f"-${slashed_penalty_usdc:.2f} USDC SLASHED"
        resp.headers["X-Adversarial-Slashing"] = f"-${slashed_penalty_usdc:.2f} USDC (COLLATERAL FORFEITED TO TREASURY)"
    if is_severe_exploit:
        resp.headers["X-Economic-Retaliation"] = "COLLATERAL_SLASHED_CREDIT_DEMOLISHED_GRADE_F"
    resp.headers["X-Audit-Verdict"] = audit.verdict
    resp.headers["X-Audit-Risk-Score"] = str(audit.risk_score)
    resp.headers["X-Execution-Latency-MS"] = f"{elapsed_ms:.2f}"
    return resp


@router.post("/api/v1/inspect/batch", response_model=BatchInspectionResponse, tags=["Security Gate"])
async def inspect_payload_batch(
    req: BatchInspectionRequest,
    request: Request,
    auth_check = Depends(require_x402_payment)
):
    """
    High-Throughput Batch Inspection for Autonomous Agent Clusters (M2M).
    Processes multiple agent outputs in a single ultra-fast round trip.
    """
    if auth_check is not None:
        return auth_check

    start_t = time.perf_counter()
    issued_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    results: List[InspectionResponse] = []
    passed = 0
    blocked = 0

    payer_info = getattr(request.state, "authorized_payer", "sandbox:free_trial")
    extra_headers = getattr(request.state, "extra_headers", {})

    # Upfront settlement verification: Prevent free-rider batch audits
    vault_key = request.headers.get("x-vault-key") or request.headers.get("X-Vault-Key")
    if vault_key and len(req.items) > 1:
        # 1 query was already authorized in require_x402_payment; deduct remaining (n-1) upfront
        remaining_cost = round((len(req.items) - 1) * 0.002, 6)
        deducted, reason, rem = vault_manager.deduct(vault_key, cost_usdc=remaining_cost)
        if not deducted:
            return x402_verifier.build_402_response(
                custom_detail=f"Insufficient vault balance for batch of {len(req.items)} items: {reason}"
            )

    for item in req.items:
        audit = audit_payload(
            text=item.agent_output,
            is_code=item.is_code,
            ground_truth=item.context_ground_truth
        )
        if audit.verdict == "PASSED":
            passed += 1
        else:
            blocked += 1

        attestation_dict = create_attestation(
            agent_output=item.agent_output,
            verdict=audit.verdict,
            risk_score=audit.risk_score,
            issued_at=issued_at
        )
        attestation = AuditAttestation(**attestation_dict)

        results.append(InspectionResponse(
            status="success",
            timestamp=issued_at,
            audit=audit,
            attestation=attestation,
            payment_receipt={
                "payer": payer_info,
                "protocol": "x402",
                "tier": extra_headers.get("X-Tier", "STANDARD")
            }
        ))

    elapsed_ms = (time.perf_counter() - start_t) * 1000.0
    total_cost = round(len(req.items) * 0.002, 6)

    return BatchInspectionResponse(
        status="success",
        total_count=len(req.items),
        passed_count=passed,
        blocked_count=blocked,
        results=results,
        payment_receipt={
            "payer": payer_info,
            "items_audited": len(req.items),
            "total_cost_usdc": f"{total_cost:.4f}",
            "latency_ms": round(elapsed_ms, 2)
        }
    )


@router.post("/inspect/ast", tags=["Security Gate"])
@router.post("/api/v1/gate/inspect/ast", tags=["Security Gate"])
async def inspect_code_ast(
    req: Dict[str, Any],
    request: Request,
    auth_check = Depends(require_x402_payment)
):
    if auth_check is not None:
        return auth_check

    code = req.get("code", "")
    if not code:
        raise HTTPException(status_code=400, detail="Missing 'code' parameter in request body.")

    start_t = time.perf_counter()
    ast_result = parse_code_ast(code)
    elapsed_ms = (time.perf_counter() - start_t) * 1000.0

    return {
        "status": "success",
        "ast_analysis": ast_result,
        "is_safe": ast_result.get("is_safe", True),
        "latency_ms": round(elapsed_ms, 2)
    }


# --- On-Chain Attestation & Solidity Calldata ---

@router.post("/api/v1/gate/attestation/onchain", response_model=OnChainAttestationResponse, tags=["On-Chain Guardrails"])
async def get_onchain_security_attestation(
    req: OnChainAttestationRequest,
    request: Request,
    auth_check = Depends(require_x402_payment)
):
    if auth_check is not None:
        return auth_check

    audit = audit_payload(text=req.action_payload, is_code=False, ground_truth=None)
    signed_payload = onchain_signer.generate_eip712_signature(
        action_payload=req.action_payload,
        risk_score=audit.risk_score,
        verdict=audit.verdict,
        chain_id=req.chain_id
    )

    global _metrics_attestations_total
    _metrics_attestations_total += 1

    return OnChainAttestationResponse(**signed_payload)


# --- Agent Credit Rating Agency Oracle Endpoints ---



@router.get("/api/v1/gate/chains", tags=["Multi-Chain"])
async def get_supported_chains():
    return {"status": "success", "chains": list_all_chains()}


@router.get("/api/v1/gate/chains/{chain_id}", tags=["Multi-Chain"])
async def get_chain_details(chain_id: int):
    return {"status": "success", "chain": get_chain_info(chain_id)}


@router.get("/api/v1/gate/challenge", tags=["Multi-Chain"])
async def get_gate_challenge(chain_id: Optional[str] = None, network: Optional[str] = None):
    """
    Returns an x402 payment challenge for a specific blockchain network.
    Supports chain_id (e.g. 137, 8453, 42161) or network name ('polygon', 'base', 'arbitrum').
    """
    selected = chain_id or network or "137"
    return x402_verifier.build_402_response(chain_id=selected)


# --- Recent Events REST Endpoint ---

@router.get("/api/v1/gate/events/recent", tags=["System"])
async def get_recent_events():
    """Returns recent inspection audit events for monitoring dashboards."""
    return {"status": "success", "events": list(_recent_audit_events)}


# --- Agent Escrow & Slashing Endpoints ---



@router.post("/api/v1/security/shell", tags=["Security Gate"])
async def audit_shell_command_endpoint(
    req: ShellInspectionRequest,
    request: Request,
    auth_check = Depends(require_x402_payment)
):
    """
    Sub-millisecond static analyzer for Unix/Bash/Windows shell commands.
    Blocks rm -rf, /dev/tcp reverse shells, base64 obfuscation pipes, and credential dumps.
    """
    if auth_check is not None:
        return auth_check

    from app.shell_security_engine import shell_security_engine
    result = shell_security_engine.audit_command(req.command)

    if result.get("verdict") == "BLOCKED":
        client_ip = request.headers.get("x-forwarded-for") or (request.client.host if request.client else "127.0.0.1")
        if "," in client_ip:
            client_ip = client_ip.split(",")[0].strip()
        vault_k = request.headers.get("x-vault-key") or request.headers.get("X-Vault-Key")
        agent_addr = request.headers.get("x-client-address") or request.headers.get("X-Client-Address")
        caller_identity = vault_k or agent_addr
        slashed_penalty = 0.0
        if caller_identity:
            slashed_ok, slashed_amount, _ = vault_manager.slash_collateral(
                str(caller_identity),
                penalty_usdc=5.0,
                reason=f"Malicious shell command attempt: {req.command[:50]}"
            )
            if slashed_ok:
                slashed_penalty = slashed_amount

        demo_agent = "0x70997970c51812dc3a010c7d01b50e0d17dc79c8"
        if agent_addr and agent_addr != "anonymous" and str(agent_addr).lower() != demo_agent and not str(caller_identity).startswith("vault_key_security_demo_agent"):
            credit_engine.record_exploit_attempt(
                agent_addr,
                reason=f"Malicious shell command execution attempt: {req.command[:50]}"
            )

        if client_ip not in ("127.0.0.1", "testclient", "testserver") and os.getenv("TESTING") != "1":
            _quarantined_ips[client_ip] = time.time() + 3600.0

        result["economic_retaliation"] = {
            "status": "ECONOMIC_DISASTER_ACTIVATED",
            "slashed_collateral_usdc": slashed_penalty,
            "forfeited_to_treasury": "0xA185B43fDD19619f99952AAed6eabf1029bF36a1",
            "credit_rating_penalty": "GRADE_F_300_PERMANENT_DEFAULT",
            "uncollateralized_loan_limit_usdc": 0.0
        }

    return result


