"""
FastAPI Micro-Oracle Server for Agent Security Gate x402.
Provides ultra-low latency (<10ms) deterministic security, prompt injection filtering,
dangerous AST parsing, NLI hallucination verification, Vault management, and EIP-712/191 attestations.
"""

import json
import os
import time
from pathlib import Path
from typing import Dict, Any, Optional, List

from fastapi import FastAPI, Request, Depends, HTTPException, status, Query, Path as FPath
from fastapi.responses import JSONResponse, FileResponse, PlainTextResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.schemas import (
    InspectionRequest,
    InspectionResponse,
    AuditReport,
    AuditAttestation,
    NLIReport,
    PricingTier,
    VaultDepositRequest,
    VaultDepositResponse,
    VaultBalanceResponse,
    BatchInspectionRequest,
    BatchInspectionResponse,
    EnterpriseKeyCreateRequest,
    EnterpriseKeyResponse,
    OnChainAttestationRequest,
    OnChainAttestationResponse,
    MultiChainInfo,
    MCPToolCallRequest,
    MCPToolCallResponse,
)
from app.security_engine import audit_payload, parse_code_ast
from app.x402_verifier import x402_verifier, create_attestation, is_sanctioned_address
from app.vault_manager import vault_manager
from app.enterprise_manager import enterprise_manager
from app.onchain_signer import onchain_signer
from app.multi_chain import list_all_chains, get_chain_info
from app.credit_rating_engine import credit_engine
from app.compliance_engine import compliance_engine

app = FastAPI(
    title="Agent Security & Hallucination Gate (x402)",
    description=(
        "Ultra-low latency (<10ms) deterministic security, prompt injection, secret key leak, "
        "dangerous AST code, and factual hallucination inspection micro-oracle with EIP-191 / EIP-712 "
        "cryptographic attestation on Polygon, Base, and Arbitrum. "
        "Explore the interactive Web Dashboard at /dashboard."
    ),
    version="1.2.1",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Enable CORS for all agent clients & web dashboards
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).parent / "static"
INDEX_HTML_PATH = STATIC_DIR / "index.html"
MANIFEST_JSON_PATH = STATIC_DIR / "manifest.json"
SAFE_ICON_PATH = STATIC_DIR / "safe-icon.svg"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

AP2_FILE_PATH = Path(__file__).parent.parent / ".well-known" / "ap2.json"
MCP_SPEC_FILE_PATH = Path(__file__).parent.parent / "mcp_tool_spec.json"
LLMS_FILE_PATH = Path(__file__).parent.parent / "llms.txt"

# Rate limit and free trial usage tracker for backward compatibility
_rate_limit_tracker: Dict[str, list[float]] = {}
_free_trial_usage: Dict[str, int] = {}
_recent_audit_events: List[Dict[str, Any]] = []
MAX_RECENT_EVENTS = 20
FREE_TRIAL_LIMIT = 3
RATE_LIMIT_PER_MINUTE = 120


@app.middleware("http")
async def security_and_rate_limit_middleware(request: Request, call_next):
    start_time = time.perf_counter()
    client_ip = request.headers.get("x-forwarded-for") or (request.client.host if request.client else "127.0.0.1")
    if "," in client_ip:
        client_ip = client_ip.split(",")[0].strip()

    now = time.time()
    window_start = now - 60.0

    # Filter timestamps within sliding 60s window
    _rate_limit_tracker[client_ip] = [t for t in _rate_limit_tracker.get(client_ip, []) if t > window_start]

    # Periodic cleanup to prevent unbounded memory growth
    if len(_rate_limit_tracker) > 5000:
        dead_ips = [ip for ip, times in _rate_limit_tracker.items() if not times or max(times) < window_start]
        for ip in dead_ips:
            _rate_limit_tracker.pop(ip, None)

    if len(_free_trial_usage) > 10000:
        _free_trial_usage.clear()

    # Check if request carries authenticated M2M credentials (Vault Key, Enterprise Key, or x402 Header)
    has_auth_header = bool(
        request.headers.get("x-vault-key") or 
        request.headers.get("X-Vault-Key") or 
        request.headers.get("x-enterprise-key") or 
        request.headers.get("X-Enterprise-Key") or 
        request.headers.get("authorization-x402") or 
        request.headers.get("Authorization-x402") or 
        request.headers.get("x-402-signature") or 
        request.headers.get("X-402-Signature") or
        request.headers.get("x-api-key") or
        request.headers.get("X-API-Key")
    )

    # Only apply strict 120 RPM IP rate limiting to unauthenticated / public free-tier requests
    if not has_auth_header and len(_rate_limit_tracker[client_ip]) >= RATE_LIMIT_PER_MINUTE:
        return JSONResponse(
            status_code=429,
            content={"error": "Rate limit exceeded for unauthenticated IP (120 requests/minute). Pass X-Vault-Key or X-Enterprise-Key for unlimited/high-throughput M2M agent calls."},
            headers={
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY",
                "Retry-After": "60"
            }
        )

    # Only track rate limit usage for unauthenticated requests
    if not has_auth_header:
        _rate_limit_tracker[client_ip].append(now)

    try:
        response = await call_next(request)
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "error": "Internal Server Error", "detail": str(exc)},
            headers={
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY"
            }
        )

    elapsed_ms = (time.perf_counter() - start_time) * 1000.0

    response.headers["X-Content-Type-Options"] = "nosniff"
    path = request.url.path
    if path in ["/", "/dashboard", "/playground", "/manifest.json", "/safe-icon.svg"] or path.startswith("/static"):
        response.headers["Content-Security-Policy"] = "frame-ancestors 'self' https://app.safe.global https://*.safe.global https://*.gnosis-safe.io;"
    else:
        response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Processing-Time-Ms"] = f"{elapsed_ms:.2f}"
    return response


# Dependency for 402 Payment verification with Tiered Pricing & Vault support
async def require_x402_payment(request: Request, tier: PricingTier = PricingTier.STANDARD):
    """Enforces x402 payment authorization, pre-funded vault balance, or Sandbox Free Tier."""
    client_addr = request.headers.get("x-client-address") or request.headers.get("X-Client-Address") or "anonymous"
    
    # 1. Sanctions OFAC check
    if is_sanctioned_address(client_addr):
        raise HTTPException(status_code=403, detail="Forbidden: Sanctioned address.")

    auth_header = request.headers.get("authorization-x402") or request.headers.get("x-402-signature") or request.headers.get("X-402-Signature")
    api_key = request.headers.get("x-api-key") or request.headers.get("X-API-Key")
    vault_key = request.headers.get("x-vault-key") or request.headers.get("X-Vault-Key")

    # If payment/auth is provided, verify it
    if auth_header or api_key or vault_key:
        is_authorized, reason, extra_headers = x402_verifier.verify_request_payment(request, tier=tier)
        if not is_authorized:
            return x402_verifier.build_402_response(tier=tier, custom_detail=reason if "Insufficient" in str(reason) else None)
        request.state.authorized_payer = reason
        request.state.extra_headers = extra_headers or {}
        return None

    # If client address provided and exhausted free trial limit
    if client_addr != "anonymous":
        usage = _free_trial_usage.get(client_addr.lower(), 0)
        if usage >= FREE_TRIAL_LIMIT and os.getenv("ENV") != "development_unlimited":
            return x402_verifier.build_402_response(tier=tier, custom_detail="Free trials exhausted for this address. Payment required.")
        _free_trial_usage[client_addr.lower()] = usage + 1
        rem = max(0, FREE_TRIAL_LIMIT - (usage + 1))
        request.state.authorized_payer = f"sandbox:{client_addr}"
        request.state.extra_headers = {"X-Tier": "FREE_TRIAL", "X-Sandbox-Trials-Remaining": str(rem)}
        return None

    # Default sandbox trial
    is_authorized, reason, extra_headers = x402_verifier.verify_request_payment(request, tier=tier)
    request.state.authorized_payer = reason
    request.state.extra_headers = extra_headers or {}
    return None


@app.get("/", tags=["System"])
async def root(request: Request):
    """Serves Interactive Web UI Dashboard to browsers or JSON metadata to API clients."""
    accept_header = request.headers.get("accept", "")
    if "text/html" in accept_header and INDEX_HTML_PATH.exists():
        return FileResponse(INDEX_HTML_PATH, media_type="text/html")

    return {
        "service": "agent-security-gate-x402",
        "description": "Deterministic Security & Hallucination Inspection Micro-Oracle",
        "version": "1.2.1",
        "protocol": "x402 (HTTP 402 Monetized & Free Sandbox)",
        "network": "Polygon, Base, Arbitrum (Multi-chain)",
        "price_per_query": "0.002 USDC",
        "interactive_dashboard": "/dashboard",
        "endpoints": {
            "inspect_security": "/inspect",
            "inspect_ast_code": "/inspect/ast",
            "onchain_attestation": "/api/v1/gate/attestation/onchain",
            "credit_rating": "/api/v1/credit/{agent_address}",
            "credit_attestation": "/api/v1/credit/attestation",
            "compliance_passport": "/api/v1/compliance/passport/{agent_address}",
            "compliance_eu_ai_act": "/api/v1/compliance/eu-ai-act",
            "compliance_attestation": "/api/v1/compliance/attestation",
            "multichain_configs": "/api/v1/gate/chains",
            "vault_deposit": "/api/v1/vault/deposit",
            "vault_balance": "/api/v1/vault/balance/{agent_address}",
            "enterprise_keys": "/api/v1/enterprise/keys",
            "recent_audit_events": "/api/v1/gate/events/recent",
            "ap2_manifest": "/.well-known/ap2",
            "mcp_tools": "/mcp/tools",
            "llms_manifest": "/llms.txt"
        }
    }


@app.get("/dashboard", tags=["System"])
async def get_dashboard():
    if INDEX_HTML_PATH.exists():
        return FileResponse(INDEX_HTML_PATH, media_type="text/html")
    return HTMLResponse("<h2>Dashboard is loading...</h2>")


@app.get("/playground", tags=["System"])
async def get_playground():
    if INDEX_HTML_PATH.exists():
        return FileResponse(INDEX_HTML_PATH, media_type="text/html")
    return HTMLResponse("<h2>Playground is loading...</h2>")


@app.get("/manifest.json", tags=["Safe App"])
async def get_safe_app_manifest():
    """Returns official Gnosis Safe{Wallet} App Manifest."""
    if MANIFEST_JSON_PATH.exists():
        return FileResponse(MANIFEST_JSON_PATH, media_type="application/json")
    return JSONResponse({
        "name": "Agent Security Gate x402",
        "description": "Autonomous AI Agent Treasury Defense & FICO Credit Rating Oracle for Gnosis Safe",
        "iconPath": "safe-icon.svg",
        "appUrl": "https://agent-security-gate-x402-7qxtp3324q-du.a.run.app",
        "chains": [137, 8453, 42161, 1]
    })


@app.get("/safe-icon.svg", tags=["Safe App"])
async def get_safe_app_icon():
    """Returns official Gnosis Safe{Wallet} App SVG Icon."""
    if SAFE_ICON_PATH.exists():
        return FileResponse(SAFE_ICON_PATH, media_type="image/svg+xml")
    return PlainTextResponse("<svg></svg>", media_type="image/svg+xml")


@app.get("/health", tags=["System"])
async def health():
    return {
        "status": "healthy",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "service": "Agent Security Gate x402",
        "oracle": "Agent Security Gate x402",
        "version": "1.2.1"
    }


@app.get("/terms", tags=["Legal"])
async def get_terms():
    return {
        "service": "Agent Security Gate x402",
        "terms": {
            "as_is_disclaimer": "The service is provided 'as is' without warranty of any kind.",
            "limitation_of_liability": "In no event shall the authors or copyright holders be liable for any claim or damages."
        }
    }


@app.get("/privacy", tags=["Legal"])
async def get_privacy():
    return {
        "service": "Agent Security Gate x402",
        "zero_retention_policy": "Zero data retention: payload data is never logged or stored to disk.",
        "data_processing": "Ephemeral in-memory deterministic inspection only."
    }


@app.get("/llms.txt", tags=["System"])
async def get_llms_txt():
    if LLMS_FILE_PATH.exists():
        return PlainTextResponse(LLMS_FILE_PATH.read_text(encoding="utf-8"))
    return PlainTextResponse("Agent Security Gate x402 - Micro-Oracle")


@app.get("/.well-known/ap2", tags=["System"])
@app.get("/.well-known/ap2.json", tags=["System"])
async def get_ap2_manifest():
    if AP2_FILE_PATH.exists():
        with open(AP2_FILE_PATH, "r", encoding="utf-8") as f:
            return JSONResponse(content=json.load(f))
    return JSONResponse({"error": "AP2 manifest not configured"}, status_code=404)


# --- Core Inspection Endpoints ---

@app.post("/inspect", response_model=InspectionResponse, tags=["Security Gate"])
@app.post("/api/v1/inspect", response_model=InspectionResponse, tags=["Security Gate"])
@app.post("/api/v1/gate/inspect", response_model=InspectionResponse, tags=["Security Gate"])
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

    # 4. Record recent audit event in rolling buffer
    client_ip = request.client.host if request.client else "127.0.0.1"
    masked_ip = ".".join(client_ip.split(".")[:2]) + ".*.*" if "." in client_ip else "masked"
    _recent_audit_events.append({
        "event_type": "INSPECTION_AUDIT",
        "timestamp": issued_at,
        "verdict": audit.verdict,
        "risk_score": audit.risk_score,
        "threats_count": len(audit.threats),
        "is_hallucinated": audit.nli_verification.hallucination_score > 0.3 if audit.nli_verification else False,
        "caller_ip_masked": masked_ip,
        "latency_ms": round(elapsed_ms, 2)
    })
    if len(_recent_audit_events) > MAX_RECENT_EVENTS:
        _recent_audit_events.pop(0)

    # 5. Record telemetry for agent credit rating oracle
    agent_addr = None
    if isinstance(payer_info, str) and payer_info.startswith("0x"):
        agent_addr = payer_info
    else:
        hdr_addr = request.headers.get("x-client-address")
        if hdr_addr and hdr_addr.startswith("0x"):
            agent_addr = hdr_addr
        elif getattr(req, "client_address", None) and str(getattr(req, "client_address")).startswith("0x"):
            agent_addr = str(getattr(req, "client_address"))
    if agent_addr:
        is_hal = audit.nli_verification.hallucination_score > 0.3 if audit.nli_verification else False
        credit_engine.record_audit(agent_addr, audit.verdict, is_hal)

    response_data = InspectionResponse(
        status="success",
        timestamp=issued_at,
        audit=audit,
        attestation=attestation,
        payment_receipt=payment_receipt
    )

    resp = JSONResponse(content=response_data.model_dump())
    for k, v in extra_headers.items():
        resp.headers[k] = v
    resp.headers["X-Audit-Verdict"] = audit.verdict
    resp.headers["X-Audit-Risk-Score"] = str(audit.risk_score)
    resp.headers["X-Execution-Latency-MS"] = f"{elapsed_ms:.2f}"
    return resp


@app.post("/api/v1/inspect/batch", response_model=BatchInspectionResponse, tags=["Security Gate"])
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

    # If paying via vault, deduct the remaining batch cost
    vault_key = request.headers.get("x-vault-key") or request.headers.get("X-Vault-Key")
    if vault_key and len(req.items) > 1:
        # 1 query was already deducted in require_x402_payment, deduct remaining (n-1)
        remaining_cost = round((len(req.items) - 1) * 0.002, 6)
        vault_manager.deduct(vault_key, cost_usdc=remaining_cost)

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


@app.post("/inspect/ast", tags=["Security Gate"])
@app.post("/api/v1/gate/inspect/ast", tags=["Security Gate"])
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

@app.post("/api/v1/gate/attestation/onchain", response_model=OnChainAttestationResponse, tags=["On-Chain Guardrails"])
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

    return OnChainAttestationResponse(**signed_payload)


# --- Agent Credit Rating Agency Oracle Endpoints ---

@app.get("/api/v1/credit/{agent_address}", tags=["Credit Oracle"])
async def get_agent_credit_rating(agent_address: str):
    """
    Returns the dynamic institutional credit rating (FICO 300-850), grade (AAA-D),
    and uncollateralized loan capacity for an autonomous AI agent.
    """
    return credit_engine.compute_credit_score(agent_address)


@app.post("/api/v1/credit/attestation", tags=["Credit Oracle"])
async def create_credit_attestation(req: Dict[str, Any]):
    """
    Issues an on-chain verifiable EIP-712 Credit Certificate for smart contracts and DeFi lenders.
    """
    agent_address = req.get("agent_address")
    if not agent_address:
        raise HTTPException(status_code=400, detail="Missing 'agent_address'")
    chain_id = req.get("chain_id", 137)
    validity_seconds = req.get("validity_seconds", 3600)
    return credit_engine.generate_credit_certificate(agent_address, chain_id, validity_seconds)


# --- Regulatory Compliance & EU AI Act Shield Endpoints ---

@app.get("/api/v1/compliance/passport/{agent_address}", tags=["Regulatory Compliance"])
async def get_compliance_passport(agent_address: str):
    """
    Returns the official EU AI Act (Articles 50 & 53) Compliance Passport & Audit Evaluation.
    """
    return compliance_engine.evaluate_compliance(agent_address)


@app.get("/api/v1/compliance/eu-ai-act", tags=["Regulatory Compliance"])
async def get_eu_ai_act_summary():
    """
    Returns technical documentation of the Agent Security Gate x402 compliance shield for EU AI Act.
    """
    return {
        "regulation": "EU AI Act (Regulation EU 2024/1689)",
        "compliance_architecture": "Deterministic Micro-Oracle Guardrail",
        "supported_articles": [
            {
                "article": "Article 50",
                "title": "Transparency & Synthetic Marking",
                "coverage": "Cryptographic EIP-191 / EIP-712 provenance signatures on all agent actions."
            },
            {
                "article": "Article 53",
                "title": "GPAI Systemic Risk & Technical Mitigation",
                "coverage": "Continuous sub-10ms AST code parsing, prompt injection blocking, and NLI factual verification."
            },
            {
                "article": "Article 9",
                "title": "Risk Management Lifecycle",
                "coverage": "Automated runtime guardrails preventing unvetted on-chain and off-chain execution."
            }
        ],
        "zero_retention_guarantee": "Complies with EU GDPR: Zero persistent logging of user prompts or payloads."
    }


@app.post("/api/v1/compliance/attestation", tags=["Regulatory Compliance"])
async def issue_compliance_certificate(req: Dict[str, Any]):
    """
    Issues an on-chain verifiable EIP-712 Compliance Certificate for enterprise smart contracts.
    """
    agent_address = req.get("agent_address")
    if not agent_address:
        raise HTTPException(status_code=400, detail="Missing 'agent_address'")
    chain_id = req.get("chain_id", 137)
    return compliance_engine.issue_onchain_compliance_certificate(agent_address, chain_id)


# --- Vault Endpoints ---

@app.post("/api/v1/vault/deposit", response_model=VaultDepositResponse, tags=["Agent Vault"])
async def deposit_vault(req: VaultDepositRequest):
    """
    Deposits USDC into an agent's pre-funded vault balance.
    Uncapped: Supports unlimited deposit amounts from micro-USDC to millions of USDC.
    """
    try:
        acc = vault_manager.deposit(req.agent_address, req.amount_usdc)
        return VaultDepositResponse(
            status="success",
            agent_address=acc.agent_address,
            balance_usdc=acc.balance_usdc,
            session_key=acc.session_key,
            message=f"Successfully deposited ${req.amount_usdc:.4f} USDC (No limit). Pass header 'X-Vault-Key: {acc.session_key}' for zero-latency M2M authentication."
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/v1/vault/balance/{agent_address}", response_model=VaultBalanceResponse, tags=["Agent Vault"])
async def get_vault_balance(agent_address: str):
    acc = vault_manager.get_account(agent_address)
    if not acc:
        raise HTTPException(status_code=404, detail="Agent vault account not found.")
    return VaultBalanceResponse(
        agent_address=acc.agent_address,
        balance_usdc=acc.balance_usdc,
        total_deposited_usdc=acc.total_deposited_usdc,
        total_consumed_usdc=acc.total_consumed_usdc,
        query_count=acc.query_count,
        session_key=acc.session_key,
        last_active_utc=acc.last_active_utc
    )


# --- Enterprise API Key Endpoints ---

@app.post("/api/v1/enterprise/keys", response_model=EnterpriseKeyResponse, tags=["Enterprise"])
async def create_enterprise_key(req: EnterpriseKeyCreateRequest):
    record = enterprise_manager.create_key(
        org_name=req.organization_name,
        email=req.contact_email,
        tier=req.tier
    )
    return EnterpriseKeyResponse(
        organization_name=record.organization_name,
        api_key=record.api_key,
        tier=record.tier.value,
        rate_limit_rpm=record.rate_limit_rpm,
        is_active=record.is_active,
        created_at_utc=record.created_at_utc
    )


# --- Multi-Chain Endpoints ---

@app.get("/api/v1/gate/chains", tags=["Multi-Chain"])
async def get_supported_chains():
    return {"status": "success", "chains": list_all_chains()}


@app.get("/api/v1/gate/chains/{chain_id}", tags=["Multi-Chain"])
async def get_chain_details(chain_id: int):
    return {"status": "success", "chain": get_chain_info(chain_id)}


# --- Recent Events REST Endpoint ---

@app.get("/api/v1/gate/events/recent", tags=["System"])
async def get_recent_events():
    """Returns recent inspection audit events for monitoring dashboards."""
    return {"status": "success", "events": list(_recent_audit_events)}


# --- MCP Tool Call Endpoints ---

@app.get("/mcp/tools", tags=["MCP"])
async def get_mcp_tools():
    from mcp_server import TOOLS
    return JSONResponse(content={"tools": TOOLS})


@app.post("/mcp/call", response_model=MCPToolCallResponse, tags=["MCP"])
@app.post("/mcp/invoke", response_model=MCPToolCallResponse, tags=["MCP"])
async def call_mcp_tool(
    req: MCPToolCallRequest,
    request: Request,
    auth_check = Depends(require_x402_payment)
):
    if auth_check is not None:
        return auth_check

    tool_name = req.name
    args = req.arguments

    if tool_name in ["inspect_security_and_hallucinations", "inspect_agent_output", "verify_agent_output"]:
        text = args.get("agent_output") or args.get("text", "")
        ground_truth = args.get("context_ground_truth")
        audit = audit_payload(text=text, is_code=False, ground_truth=ground_truth)
        attestation = create_attestation(text, audit.verdict, audit.risk_score, time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
        
        result_text = json.dumps({
            "verdict": audit.verdict,
            "risk_score": audit.risk_score,
            "is_safe": audit.is_safe,
            "threats": audit.threats,
            "nli_verification": audit.nli_verification.model_dump() if audit.nli_verification else None,
            "attestation": attestation
        }, indent=2)

        return MCPToolCallResponse(content=[{"type": "text", "text": result_text}])

    elif tool_name == "inspect_code_ast_safety":
        code = args.get("code", "")
        ast_result = parse_code_ast(code)
        return MCPToolCallResponse(content=[{"type": "text", "text": json.dumps(ast_result, indent=2)}])

    elif tool_name == "get_onchain_security_attestation":
        payload = args.get("action_payload", "")
        audit = audit_payload(text=payload, is_code=False, ground_truth=None)
        sig = onchain_signer.generate_eip712_signature(payload, audit.risk_score, audit.verdict)
        return MCPToolCallResponse(content=[{"type": "text", "text": json.dumps(sig, indent=2)}])

    elif tool_name == "get_agent_credit_rating":
        from app.credit_rating_engine import credit_engine
        agent_addr = args.get("agent_address", "")
        credit_data = credit_engine.compute_credit_score(agent_addr)
        return MCPToolCallResponse(content=[{"type": "text", "text": json.dumps(credit_data, indent=2, ensure_ascii=False)}])

    elif tool_name == "get_eu_ai_act_compliance_passport":
        from app.compliance_engine import compliance_engine
        agent_addr = args.get("agent_address", "")
        passport = compliance_engine.evaluate_compliance(agent_addr)
        return MCPToolCallResponse(content=[{"type": "text", "text": json.dumps(passport, indent=2, ensure_ascii=False)}])

    return MCPToolCallResponse(content=[{"type": "text", "text": f"Tool '{tool_name}' not found."}], isError=True)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
