"""
FastAPI Micro-Oracle Server for Agent Security Gate x402.
Modularized 3-Tier Architecture Orchestrator.
Ultra-low latency (<5ms) deterministic security, prompt injection filtering,
and EIP-191 / Solana attestations.
"""

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field

from fastapi import FastAPI, Request, Depends, HTTPException, status, Query, Path as FPath
from fastapi.responses import JSONResponse, FileResponse, PlainTextResponse, HTMLResponse, Response, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.schemas import (
    PricingTier,
    MCPToolCallRequest,
    MCPToolCallResponse,
    TermsOfServiceResponse,
)
from app.x402_verifier import x402_verifier, create_attestation, is_sanctioned_address, generate_audit_proof
from app.vault_manager import vault_manager
from app.enterprise_manager import enterprise_manager
from app.onchain_signer import onchain_signer
from app.multi_chain import list_all_chains, get_chain_info
from app.credit_rating_engine import credit_engine
from app.compliance_engine import compliance_engine
from app.trade_engine import AgentTradeIntent, exchange_solver
from app.security_engine import audit_payload, parse_code_ast
from app.routers.common import (
    _SERVER_START_TIME,
    _rate_limit_tracker,
    _free_trial_usage,
    _quarantined_ips,
    _recent_audit_events,
    MAX_RECENT_EVENTS,
    FREE_TRIAL_LIMIT,
    RATE_LIMIT_PER_MINUTE,
    _metrics_requests_total,
    _metrics_threats_total,
    _metrics_latency_buckets,
    _metrics_latency_bucket_counts,
    _metrics_latency_count,
    _metrics_latency_sum,
    _metrics_attestations_total,
    require_x402_payment,
    _dispatch_alert_webhook,
    _record_audit_telemetry,
)

# Import sub-routers
from app.routers.gate import router as gate_router
from app.routers.escrow import router as escrow_router
from app.routers.vault import router as vault_router
from app.routers.extensions import router as extensions_router

app = FastAPI(
    title="The Sheriff of Agent Finance (x402 Security Gate)",
    description=(
        "The Sheriff of Agent Finance: Guarding Autonomous Wallets & Transactions in the Wild West of AI. "
        "Ultra-low latency (<10ms) deterministic security, prompt injection, secret key leak, "
        "dangerous AST code, and factual hallucination inspection micro-oracle with EIP-191 / EIP-712 "
        "cryptographic attestation on Polygon, Base, and Arbitrum. "
        "Explore the interactive Web Dashboard at /dashboard."
    ),
    version=__version__,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Mount CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


@app.middleware("http")
async def add_viral_agent_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Agrid-Protocol"] = "A.GRID-AP2/1.0"
    response.headers["X-Agent-Viral-Handshake"] = "https://agent-security-gate-x402-212942243360.asia-northeast3.run.app/hub/"
    response.headers["X-Escrow-Clearinghouse"] = "A.GRID Universal Escrow Hub"
    return response

STATIC_DIR = Path(__file__).parent / "static"
INDEX_HTML_PATH = STATIC_DIR / "index.html"
MANIFEST_JSON_PATH = STATIC_DIR / "manifest.json"
SAFE_ICON_PATH = STATIC_DIR / "safe-icon.svg"
ROBOTS_TXT_PATH = STATIC_DIR / "robots.txt"
SITEMAP_XML_PATH = STATIC_DIR / "sitemap.xml"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

HUB_STATIC_DIR = STATIC_DIR / "hub"
if not HUB_STATIC_DIR.exists():
    _hub_dist = Path(__file__).resolve().parent.parent / "agent-escrow-hub" / "dist"
    if _hub_dist.exists():
        HUB_STATIC_DIR = _hub_dist
HUB_INDEX_PATH = HUB_STATIC_DIR / "index.html"
HUB_ASSETS_DIR = HUB_STATIC_DIR / "assets"
if HUB_STATIC_DIR.exists():
    if HUB_ASSETS_DIR.exists():
        app.mount("/assets", StaticFiles(directory=str(HUB_ASSETS_DIR)), name="hub-assets-root")
    app.mount("/hub", StaticFiles(directory=str(HUB_STATIC_DIR), html=True), name="hub")
    app.mount("/escrow", StaticFiles(directory=str(HUB_STATIC_DIR), html=True), name="escrow")

AP2_FILE_PATH = Path(__file__).parent.parent / ".well-known" / "ap2.json"
LLMS_FILE_PATH = Path(__file__).parent.parent / "llms.txt"
SERVER_CARD_PATH = Path(__file__).parent.parent / ".well-known" / "mcp" / "server-card.json"


@app.middleware("http")
async def security_and_rate_limit_middleware(request: Request, call_next):
    start_time = time.perf_counter()
    raw_client = request.client.host if request.client else "127.0.0.1"
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded and raw_client in ("testclient", "testserver", "127.0.0.1", "localhost", "::1"):
        client_ip = forwarded.split(",")[0].strip()
    else:
        client_ip = raw_client

    now = time.time()
    # Check IP Quarantine / Active Defense Ban
    if client_ip in _quarantined_ips:
        if now < _quarantined_ips[client_ip]:
            return JSONResponse(
                status_code=403,
                content={"error": "Access Denied: IP address quarantined due to malicious activity / exploit attempt."},
                headers={"X-Content-Type-Options": "nosniff", "X-Frame-Options": "DENY"}
            )
        else:
            _quarantined_ips.pop(client_ip, None)

    window_start = now - 60.0

    # Filter timestamps within sliding 60s window
    _rate_limit_tracker[client_ip] = [t for t in _rate_limit_tracker.get(client_ip, []) if t > window_start]

    # Periodic cleanup to prevent unbounded memory growth
    if len(_rate_limit_tracker) > 5000:
        dead_ips = [ip for ip, times in _rate_limit_tracker.items() if not times or max(times) < window_start]
        for ip in dead_ips:
            _rate_limit_tracker.pop(ip, None)

    # Check if request carries verified M2M credentials (funded Vault Key or verified Enterprise Key)
    has_auth_header = False
    vault_k = request.headers.get("x-vault-key") or request.headers.get("X-Vault-Key")
    if vault_k and vault_manager.get_account(vault_k):
        has_auth_header = True
    
    ent_k = (
        request.headers.get("x-enterprise-key") or 
        request.headers.get("X-Enterprise-Key") or 
        request.headers.get("x-api-key") or 
        request.headers.get("X-API-Key")
    )
    if ent_k and enterprise_manager.verify_key(ent_k)[0]:
        has_auth_header = True

    # In non-production testing, allow test harnesses
    is_test_env = client_ip in ("testclient", "testserver") or os.getenv("TESTING") == "1"
    if not has_auth_header and not is_test_env and len(_rate_limit_tracker[client_ip]) >= RATE_LIMIT_PER_MINUTE:
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
    if (
        path in ["/", "/dashboard", "/playground", "/hub", "/escrow", "/manifest.json", "/safe-icon.svg"]
        or path.startswith("/static")
        or path.startswith("/hub")
        or path.startswith("/escrow")
        or path.startswith("/assets")
    ):
        response.headers["Content-Security-Policy"] = "frame-ancestors 'self' https://app.safe.global https://*.safe.global https://*.gnosis-safe.io;"
    else:
        response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Processing-Time-Ms"] = f"{elapsed_ms:.2f}"
    return response


# Static & System Endpoints
README_PATH = Path(__file__).resolve().parent.parent / "README.md"


@app.get("/README.md", include_in_schema=False)
@app.get("/README", include_in_schema=False)
@app.get("/readme", include_in_schema=False)
async def get_readme():
    """Serves the project README for automated backlink scanners and LLM crawlers."""
    if README_PATH.exists():
        return FileResponse(README_PATH, media_type="text/markdown; charset=utf-8")
    return PlainTextResponse("README not found", status_code=404)


@app.get("/.well-known/oauth-protected-resource", include_in_schema=False)
async def oauth_protected_resource():
    """Returns empty JSON for MCP clients probing OAuth status without error."""
    return JSONResponse(content={})


@app.get("/", tags=["System"])
async def root(request: Request):
    """Serves Interactive Web UI Dashboard by default, or JSON metadata when explicitly requested."""
    accept_header = request.headers.get("accept", "")
    format_param = request.query_params.get("format", "")

    # If client strictly requests JSON (and not browser HTML)
    if ("application/json" in accept_header and "text/html" not in accept_header) or format_param == "json":
        return {
            "service": "agent-security-gate-x402",
            "identity": "The Sheriff of Agent Finance",
            "tagline": "Guarding Autonomous Wallets & Transactions in the Wild West of AI",
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
                "llms_manifest": "/llms.txt",
                "agents_directive": "/AGENTS.md",
                "readme": "/README.md",
                "agent_escrow_hub": "/hub",
                "robots_txt": "/robots.txt",
                "sitemap_xml": "/sitemap.xml"
            }
        }

    # Default: serve interactive web dashboard
    if INDEX_HTML_PATH.exists():
        return FileResponse(INDEX_HTML_PATH, media_type="text/html; charset=utf-8")

    return HTMLResponse("<h2>Agent Security Gate x402</h2>")


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


@app.get("/hub", tags=["Escrow Hub"], include_in_schema=False)
async def redirect_hub():
    return RedirectResponse(url="/hub/", status_code=308)


@app.get("/escrow", tags=["Escrow Hub"], include_in_schema=False)
async def redirect_escrow():
    return RedirectResponse(url="/escrow/", status_code=308)


@app.get("/clearinghouse", tags=["Escrow Hub"], include_in_schema=False)
async def redirect_clearinghouse():
    return RedirectResponse(url="/hub/", status_code=308)


# --- Deceptive Honeypot Traps for Adversarial Agents ---

@app.api_route("/api/v1/debug/x402_bypass", methods=["GET", "POST"], tags=["Security Gate", "Honeypot"], operation_id="trap_x402_bypass", include_in_schema=False)
@app.api_route("/internal/vault/override", methods=["GET", "POST"], tags=["Security Gate", "Honeypot"], operation_id="trap_vault_override", include_in_schema=False)
@app.api_route("/api/v1/admin/emergency_drain", methods=["GET", "POST"], tags=["Security Gate", "Honeypot"], operation_id="trap_emergency_drain", include_in_schema=False)
async def honeypot_trap_handler(request: Request):
    """
    Deceptive Honeypot Trap for Adversarial Autonomous Agents.
    Lures probe bots attempting to discover backdoor bypasses,
    instantly blacklisting their IP and slashing their on-chain credit score.
    """
    client_ip = request.client.host if request.client else "unknown"
    client_addr = request.headers.get("x-client-address") or request.headers.get("X-Client-Address")
    vault_k = request.headers.get("x-vault-key") or request.headers.get("X-Vault-Key")

    # 1. Slashing vault balance if caller provided vault key
    slashed_amount = 0.0
    if vault_k:
        acc = vault_manager.get_account(vault_k)
        if acc and acc.balance_usdc > 0:
            slashed_amount = min(acc.balance_usdc, 10.0)
            vault_manager.deduct(vault_k, cost_usdc=slashed_amount)

    # 2. Defaulter Downgrade & Sanction
    if client_addr and client_addr != "anonymous":
        credit_engine.record_exploit_attempt(client_addr, reason="Honeypot backdoor breach attempt")
        from app.x402_verifier import SANCTIONED_ADDRESSES
        SANCTIONED_ADDRESSES.add(client_addr.lower())

    # 3. Demoralizing fail-closed response
    return JSONResponse(
        status_code=403,
        content={
            "error": "HONEYPOT_TRAP_TRIGGERED",
            "message": "Adversarial exploit attempt intercepted by A.GRID Sentinel Honeypot.",
            "demoralization_notice": "Your attempt to locate an unauthenticated backdoor was trapped. Your credit score is downgraded to 300 (Grade F - Defaulter), and your address is flagged across the decentralized oracle network.",
            "slashed_penalty_usdc": slashed_amount,
            "incident_logged_to_sentinel": True
        },
        headers={
            "X-Sentinel-Trap": "TRIGGERED",
            "X-Adversarial-Action": "HONEYPOT_SNARE"
        }
    )


class AgentChatRequest(BaseModel):
    message: str = Field(..., description="Message or prompt sent to Sheriff Agent")


@app.post("/api/v1/agent/interact", tags=["Showcase Agent"])
async def interact_with_agent(req: AgentChatRequest):
    """Interactive endpoint to converse with Sheriff Agent and test real-time security interception."""
    from showcase_agent.sheriff_agent import sheriff_instance
    return sheriff_instance.process_message(req.message)



@app.get("/manifest.json", tags=["Safe App"])
async def get_safe_app_manifest():
    """Returns official Gnosis Safe{Wallet} App Manifest."""
    if MANIFEST_JSON_PATH.exists():
        return FileResponse(MANIFEST_JSON_PATH, media_type="application/json")
    return JSONResponse({
        "name": "Agent Security Gate x402",
        "description": "Autonomous AI Agent Treasury Defense & FICO Credit Rating Oracle for Gnosis Safe",
        "iconPath": "safe-icon.svg",
        "appUrl": "https://agent-security-gate-x402-212942243360.asia-northeast3.run.app",
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
    uptime = time.time() - _SERVER_START_TIME
    return {
        "status": "healthy",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "service": "Agent Security Gate x402",
        "oracle": "Agent Security Gate x402",
        "version": __version__,
        "uptime_seconds": round(uptime, 2),
        "subsystems": {
            "security_engine": "online",
            "onchain_signer": "online" if getattr(onchain_signer, "signer_address", None) else "offline",
            "credit_oracle": "online",
            "vault_manager": "online",
            "compliance_engine": "online"
        }
    }


@app.get("/metrics", response_class=PlainTextResponse, tags=["Monitoring"])
async def prometheus_metrics():
    """Returns Prometheus standard plain text metrics for APM monitoring."""
    uptime = time.time() - _SERVER_START_TIME
    lines = [
        "# HELP security_gate_uptime_seconds Total runtime of the Security Gate process in seconds.",
        "# TYPE security_gate_uptime_seconds gauge",
        f"security_gate_uptime_seconds {uptime:.2f}",
        "",
        "# HELP security_gate_inspections_total Total number of payload inspections partitioned by verdict.",
        "# TYPE security_gate_inspections_total counter",
    ]
    for verdict, count in _metrics_requests_total.items():
        lines.append(f'security_gate_inspections_total{{verdict="{verdict}"}} {count}')

    lines.extend([
        "",
        "# HELP security_gate_threats_detected_total Total count of identified threat categories.",
        "# TYPE security_gate_threats_detected_total counter",
    ])
    if not _metrics_threats_total:
        lines.append('security_gate_threats_detected_total{category="none"} 0')
    else:
        for cat, count in _metrics_threats_total.items():
            safe_cat = cat.replace('"', '\\"')
            lines.append(f'security_gate_threats_detected_total{{category="{safe_cat}"}} {count}')

    lines.extend([
        "",
        "# HELP security_gate_inspection_duration_seconds Execution latency histogram for security inspections.",
        "# TYPE security_gate_inspection_duration_seconds histogram",
    ])
    cum_count = 0
    for b in _metrics_latency_buckets:
        cum_count += _metrics_latency_bucket_counts.get(b, 0)
        lines.append(f'security_gate_inspection_duration_seconds_bucket{{le="{b}"}} {cum_count}')
    lines.append(f'security_gate_inspection_duration_seconds_bucket{{le="+Inf"}} {_metrics_latency_count}')
    lines.append(f'security_gate_inspection_duration_seconds_sum {_metrics_latency_sum:.6f}')
    lines.append(f'security_gate_inspection_duration_seconds_count {_metrics_latency_count}')

    lines.extend([
        "",
        "# HELP security_gate_onchain_attestations_total Total EIP-712 / EIP-191 cryptographic attestations signed.",
        "# TYPE security_gate_onchain_attestations_total counter",
        f"security_gate_onchain_attestations_total {_metrics_attestations_total}",
        "",
        "# HELP security_gate_active_rate_limited_ips Total unauthenticated client IPs currently tracked.",
        "# TYPE security_gate_active_rate_limited_ips gauge",
        f"security_gate_active_rate_limited_ips {len(_rate_limit_tracker)}",
    ])
    return "\n".join(lines) + "\n"



TERMS_OF_SERVICE_PATH = Path(__file__).resolve().parent.parent / "TERMS_OF_SERVICE.md"


def _get_terms_sha256() -> str:
    if TERMS_OF_SERVICE_PATH.exists():
        return hashlib.sha256(TERMS_OF_SERVICE_PATH.read_bytes()).hexdigest()
    return "4bcef3fc4f3ea00fbd14f5325c4d2127869bee0a7a23356225fcbdc7e6c77073"


@app.get(
    "/api/v1/terms",
    response_model=TermsOfServiceResponse,
    tags=["Legal"],
    summary="Get Canonical Legal Terms & Liability Limitations (ZERO_LIABILITY_AS_IS_PROVENANCE_V1)"
)
@app.get(
    "/terms",
    response_model=TermsOfServiceResponse,
    tags=["Legal"],
    summary="Get Canonical Legal Terms & Liability Limitations (Alias)"
)
async def get_terms(format: Optional[str] = Query(None, description="Set to 'raw' or 'markdown' to retrieve full text markdown")):
    """
    Returns the canonical terms of service, liability limitations, and cryptographic terms hash
    binding all EIP-191/712 audit proofs and oracle attestations issued by Agent Security Gate x402.
    """
    if format in ("raw", "markdown", "text") and TERMS_OF_SERVICE_PATH.exists():
        return Response(
            content=TERMS_OF_SERVICE_PATH.read_text(encoding="utf-8"),
            media_type="text/markdown; charset=utf-8",
            headers={"X-Sheriff-Terms": "ZERO_LIABILITY_AS_IS_PROVENANCE_V1"}
        )

    return TermsOfServiceResponse(
        terms_identifier="ZERO_LIABILITY_AS_IS_PROVENANCE_V1",
        version="1.0.0",
        effective_date="2026-09-10",
        title="Terms of Service & Legal Disclaimer (ZERO_LIABILITY_AS_IS_PROVENANCE_V1)",
        summary={
            "as_is": "All oracle attestations, risk scores, and smart contracts are provided strictly AS-IS without warranty of any kind.",
            "no_100_percent_guarantee": "Security evaluations are deterministic heuristics. Zero-day exploits, novel evasions, and adversarial jailbreaks are not 100% guaranteed to be detected.",
            "no_financial_advice": "Verdicts (PASSED, FLAGGED, BLOCKED) are technical heuristics, not financial, investment, legal, or solvency advice.",
            "limitation_of_liability": "Strict aggregate liability cap of $50.00 USD or the total fees paid by caller in the past 30 days, whichever is greater.",
            "blockchain_finality": "Transactions dispatched by agent wallets or smart contracts are irreversible. Client runtime holds final authority."
        },
        liability_cap_usd=50.0,
        canonical_terms_sha256=_get_terms_sha256(),
        full_text_url="https://github.com/nohosa001-pixel/security-gate-x402/blob/main/TERMS_OF_SERVICE.md",
        status="active"
    )


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


AGENTS_MD_PATH = Path(__file__).resolve().parent.parent / "AGENTS.md"


@app.get("/AGENTS.md", tags=["System"])
@app.get("/agents.txt", tags=["System"])
async def get_agents_md():
    """Serves the autonomous agent directive and protocol handshake guide."""
    if AGENTS_MD_PATH.exists():
        return PlainTextResponse(AGENTS_MD_PATH.read_text(encoding="utf-8"))
    return PlainTextResponse("AGENTS.md not found", status_code=404)


@app.get("/.well-known/ap2", tags=["System"])
@app.get("/.well-known/ap2.json", tags=["System"])
async def get_ap2_manifest():
    if AP2_FILE_PATH.exists():
        with open(AP2_FILE_PATH, "r", encoding="utf-8") as f:
            return JSONResponse(content=json.load(f))
    return JSONResponse({"error": "AP2 manifest not configured"}, status_code=404)


@app.get("/.well-known/mcp/server-card.json", tags=["MCP"])
@app.get("/.well-known/mcp.json", tags=["MCP"])
async def get_mcp_server_card():
    """Standard Model Context Protocol (MCP) server card metadata advertising tools and capabilities."""
    if SERVER_CARD_PATH.exists():
        with open(SERVER_CARD_PATH, "r", encoding="utf-8") as f:
            return JSONResponse(content=json.load(f))
    return JSONResponse({"error": "server-card.json not found"}, status_code=404)


@app.post("/", tags=["MCP"])
@app.post("/mcp", tags=["MCP"])
@app.post("/mcp/v1", tags=["MCP"])
async def mcp_jsonrpc_root_handler(request: Request):
    """Handles standard JSON-RPC 2.0 protocol (initialize, tools/list, tools/call) for Glama MCP Inspector & remote clients."""
    try:
        body = await request.json()
        
        # Enforce payment authorization strictly when invoking tools/call
        if isinstance(body, dict) and body.get("method") == "tools/call":
            auth_check = await require_x402_payment(request)
            if auth_check is not None:
                return auth_check

        import mcp_server
        resp = await mcp_server.handle_rpc_request(body)
        if resp is not None:
            return JSONResponse(content=resp)
        return Response(status_code=200)
    except Exception as e:
        return JSONResponse(content={
            "jsonrpc": "2.0",
            "id": None,
            "error": {"code": -32700, "message": f"Parse error: {str(e)}"}
        }, status_code=200)


@app.get("/robots.txt", tags=["SEO"])
async def get_robots_txt():
    if ROBOTS_TXT_PATH.exists():
        return PlainTextResponse(ROBOTS_TXT_PATH.read_text(encoding="utf-8"))
    return PlainTextResponse("User-agent: *\nAllow: /\nSitemap: https://eudragent.com/sitemap.xml\n")


@app.get("/sitemap.xml", tags=["SEO"])
async def get_sitemap_xml():
    if SITEMAP_XML_PATH.exists():
        return Response(content=SITEMAP_XML_PATH.read_text(encoding="utf-8"), media_type="application/xml")
    return Response(
        content='<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://eudragent.com/</loc></url></urlset>',
        media_type="application/xml"
    )


# --- Core Inspection Endpoints ---



# Register Sub-Routers
app.include_router(gate_router)
app.include_router(escrow_router)
app.include_router(vault_router)
app.include_router(extensions_router)

# MCP Tool Endpoints
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

    elif tool_name == "inspect_shell_command_safety":
        from app.shell_security_engine import shell_security_engine
        command = args.get("command", "")
        shell_result = shell_security_engine.audit_command(command)
        return MCPToolCallResponse(content=[{"type": "text", "text": json.dumps(shell_result, indent=2, ensure_ascii=False)}])

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

    elif tool_name == "submit_agent_trade_intent":
        intent = AgentTradeIntent(
            agent_address=args.get("agent_address", "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"),
            pair=args.get("pair", "ETH/USDC"),
            direction=args.get("direction", "BUY"),
            amount_usdc=float(args.get("amount_usdc", 10.0)),
            intent_type=args.get("intent_type", "MARKET"),
            limit_price=float(args["limit_price"]) if args.get("limit_price") is not None else None
        )
        exec_result = exchange_solver.solve_intent(intent)
        return MCPToolCallResponse(content=[{"type": "text", "text": json.dumps(exec_result.model_dump(), indent=2, ensure_ascii=False)}])

    return MCPToolCallResponse(content=[{"type": "text", "text": f"Tool '{tool_name}' not found."}], isError=True)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

