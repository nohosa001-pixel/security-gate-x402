import json
import logging
import os
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
from fastapi import FastAPI, Header, Response, status, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.schemas import (
    InspectionRequest, 
    InspectionResponse, 
    AuditReport, 
    AuditAttestation,
    PaymentDemand402,
    MCPToolCallRequest,
    MCPToolCallResponse,
)
from app.security_engine import analyze_payload_security
from app.x402_verifier import verify_x402_payment, create_attestation, X402Verifier

# Load environment variables from .env if present
load_dotenv()

# Structured JSON Logger Setup
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("security_gate")

app = FastAPI(
    title="Agent Output Security & Hallucination Gate (x402)",
    description="Deterministic, ultra-low latency security and hallucination inspection micro-oracle for autonomous agents. Monetized via HTTP 402 on Polygon ($0.002 USDC).",
    version="1.0.0"
)

# Enable CORS for agent runtimes and web callers
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "120"))
_rate_limit_tracker: Dict[str, List[float]] = defaultdict(list)


@app.middleware("http")
async def rate_limit_and_log_middleware(request: Request, call_next):
    start_time = time.perf_counter()
    client_ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip() or (request.client.host if request.client else "unknown")
    now = time.time()

    # Rate Limiting (Sliding 60s Window)
    if client_ip != "127.0.0.1" and client_ip != "unknown":
        window = _rate_limit_tracker[client_ip]
        # Purge timestamps older than 60s
        _rate_limit_tracker[client_ip] = [ts for ts in window if now - ts < 60.0]
        if len(_rate_limit_tracker[client_ip]) >= RATE_LIMIT_PER_MINUTE:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"error": "Rate limit exceeded", "message": f"Maximum {RATE_LIMIT_PER_MINUTE} requests per minute allowed."},
                headers={"Retry-After": "60"}
            )
        _rate_limit_tracker[client_ip].append(now)

    response = await call_next(request)
    duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

    # Security Headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Processing-Time-Ms"] = str(duration_ms)

    # Structured JSON log for GCP Cloud Logging
    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "method": request.method,
        "path": request.url.path,
        "status_code": response.status_code,
        "duration_ms": duration_ms,
        "client_ip": client_ip
    }
    logger.info(json.dumps(log_entry))

    return response

raw_wallet = os.getenv("SERVER_WALLET_ADDRESS", "0x255F9991233f86B29dB847c8d5b8CB9915e80dCf")
SERVER_WALLET = raw_wallet.strip().split()[0]
PRICE_USDC = os.getenv("PRICE_USDC", "0.002")
NETWORK = os.getenv("NETWORK", "polygon")



@app.get("/")
async def root():
    return {
        "service": "Agent Output Security & Hallucination Gate (x402)",
        "status": "online",
        "protocol": "x402",
        "network": NETWORK,
        "pricing_usdc": PRICE_USDC,
        "docs_url": "/docs",
        "discovery_manifest": "/.well-known/ap2",
        "terms_of_service": "/terms",
        "privacy_policy": "/privacy"
    }


@app.get("/health")
@app.get("/v1/health")
async def health_check():
    return {
        "status": "ok",
        "service": "agent-security-gate-x402",
        "version": "1.0.0",
        "protocol": "x402",
        "network": NETWORK,
        "pricing_usdc": PRICE_USDC
    }


@app.get("/terms", tags=["Legal"])
async def terms_of_service():
    """Legal Terms of Service and Disclaimers."""
    return {
        "service_name": "Agent Output Security & Hallucination Gate (x402)",
        "effective_date": "2026-01-01",
        "terms": {
            "license": "Permission is granted to autonomous agents and human developers to invoke this micro-oracle for verification purposes upon payment of the required x402 protocol fee.",
            "as_is_disclaimer": "THE SERVICE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND NON-INFRINGEMENT.",
            "limitation_of_liability": f"IN NO EVENT SHALL THE OPERATORS OR SERVICE PROVIDERS BE LIABLE FOR ANY CLAIM, DAMAGES, OR OTHER LIABILITY ARISING FROM, OUT OF, OR IN CONNECTION WITH THE USE OR INABILITY TO USE THE SERVICE. LIABILITY SHALL IN ALL CIRCUMSTANCES BE LIMITED EXCLUSIVELY TO THE AGGREGATE FEES PAID FOR THE DISPUTED REQUEST (${PRICE_USDC} USDC).",
            "sanctions_compliance": "Interaction with this service from OFAC-sanctioned addresses or jurisdictions is strictly prohibited and subject to automatic algorithmic refusal."
        }
    }


@app.get("/privacy", tags=["Legal"])
async def privacy_policy():
    """Privacy Policy & Zero-Data-Retention Declaration."""
    return {
        "service_name": "Agent Output Security & Hallucination Gate (x402)",
        "policy_version": "1.0.0",
        "zero_retention_policy": {
            "data_storage": "Zero-Retention. Payloads submitted for inspection (agent outputs, code, and context) are processed strictly in-memory and immediately discarded upon response delivery.",
            "database_logging": "No persistent storage, database, or disk logging of customer inputs or outputs is maintained.",
            "secret_redaction": "Detected secrets, private keys, or API tokens are masked and redacted in-memory prior to inclusion in the diagnostic audit report.",
            "telemetry": "Only aggregate, non-identifying telemetry (e.g., latency ms, threat category counters) and on-chain blockchain receipts are preserved."
        }
    }


@app.get("/.well-known/ap2")
@app.get("/.well-known/ap2.json")
async def ap2_manifest():
    return {
        "protocol": "AP2/1.0",
        "service": "Agent Output Security & Hallucination Gate",
        "supported_rails": ["x402-polygon-usdc"],
        "pricing": {"amount": PRICE_USDC, "currency": "USDC", "network": NETWORK},
        "capabilities": [
            {
                "action": "inspect_agent_output",
                "endpoint": "/api/v1/inspect",
                "description": "Ultra-low latency security, key leak, and factual hallucination validator for 0.002 USDC."
            },
            {
                "action": "mcp_tool_invoke",
                "endpoint": "/mcp/invoke",
                "description": "Direct JSON-RPC standard MCP tool dispatcher with x402 payment validation."
            }
        ],

        "legal": {
            "terms": "/terms",
            "privacy": "/privacy"
        }
    }


FREE_TRIAL_LIMIT = int(os.getenv("FREE_TRIAL_LIMIT", "3"))
_free_trial_tracker: Dict[str, int] = {}


def get_client_id(request: Request, client_address: Optional[str] = None) -> str:
    if client_address:
        return client_address.lower().strip()
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "anonymous-guest"


@app.post("/api/v1/inspect", response_model=InspectionResponse)
@app.post("/v1/inspect", response_model=InspectionResponse)
@app.post("/inspect", response_model=InspectionResponse)
async def inspect_payload(
    req: InspectionRequest,
    request: Request,
    authorization_x402: Optional[str] = Header(None, alias="Authorization-x402"),
    client_address: Optional[str] = Header(None, alias="X-Client-Address"),
    x_trial: Optional[str] = Header(None, alias="X-Trial")
):
    client_id = get_client_id(request, client_address)
    used_trials = _free_trial_tracker.get(client_id, 0)
    is_free_trial = False

    # Check if request qualifies for Free Trial
    if not authorization_x402 or not client_address:
        if used_trials < FREE_TRIAL_LIMIT or x_trial == "true":
            is_free_trial = True
            _free_trial_tracker[client_id] = used_trials + 1
        else:
            challenge = X402Verifier.generate_challenge(
                pay_to=SERVER_WALLET,
                amount_usdc=PRICE_USDC
            )
            return JSONResponse(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                headers={
                    "X-Payment-Protocol": "x402",
                    "X-Payment-Network": NETWORK,
                    "X-Payment-Token": "USDC",
                    "X-Payment-Amount": PRICE_USDC,
                    "X-Payment-Recipient": SERVER_WALLET,
                    "X-Payment-Resource": "/api/v1/inspect",
                    "X-Free-Trials-Exhausted": "true"
                },
                content=challenge.model_dump()
            )
    else:
        is_valid = await verify_x402_payment(
            authorization_header=authorization_x402,
            client_address=client_address,
            expected_amount=PRICE_USDC,
            recipient=SERVER_WALLET
        )
        if not is_valid:
            return Response(status_code=status.HTTP_403_FORBIDDEN, content="Invalid x402 payment signature or sanctioned client address.")

    audit_result = analyze_payload_security(
        content=req.agent_output,
        is_code=req.is_code,
        context_ground_truth=req.context_ground_truth
    )

    now_iso = datetime.now(timezone.utc).isoformat()
    audit_obj = AuditReport(**audit_result)
    
    # Generate cryptographic attestation receipt
    attestation_data = create_attestation(
        agent_output=req.agent_output,
        verdict=audit_obj.verdict,
        risk_score=audit_obj.risk_score,
        issued_at=now_iso
    )

    remaining_trials = max(0, FREE_TRIAL_LIMIT - _free_trial_tracker.get(client_id, 0))
    payment_info = {
        "tier": "FREE_TRIAL" if is_free_trial else "PAID_X402",
        "amount": "0.0000" if is_free_trial else PRICE_USDC,
        "currency": "USDC",
        "network": NETWORK,
        "recipient": SERVER_WALLET,
        "remaining_free_trials": remaining_trials if is_free_trial else "unlimited"
    }

    return InspectionResponse(
        status="success",
        timestamp=now_iso,
        audit=audit_obj,
        attestation=AuditAttestation(**attestation_data),
        payment_receipt=payment_info
    )


@app.get("/mcp/tools", tags=["MCP Tools"])
async def list_mcp_tools():
    """Returns available MCP Tools metadata in standard format."""
    tool_spec_path = Path(__file__).resolve().parent.parent / "mcp_tool_spec.json"
    if tool_spec_path.exists():
        with open(tool_spec_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "tools": [
            {
                "name": "inspect_agent_output",
                "description": "Inspects an AI agent's text or code output for prompt injections, private key/secret leaks, dangerous AST executions, and factual/numerical hallucinations against ground truth. Issues a cryptographic EIP-191 Proof-of-Safety attestation. Free trial tier enabled.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "agent_output": {
                            "type": "string", 
                            "description": "The textual or code output generated by an LLM / agent to inspect",
                            "default": "Quarterly net revenue reached $1.2M with zero infrastructure failures."
                        },
                        "is_code": {
                            "type": "boolean", 
                            "default": False, 
                            "description": "Set to true if agent_output is executable Python / shell code"
                        },
                        "context_ground_truth": {
                            "type": "string", 
                            "description": "Original factual reference / context to verify numerical accuracy",
                            "default": "Revenue report: Q3 net revenue is $1.2M."
                        }
                    },
                    "required": ["agent_output"]
                }
            }
        ]
    }


@app.post("/mcp/invoke", response_model=MCPToolCallResponse, tags=["MCP Tools"])
async def invoke_mcp_tool(
    tool_call: MCPToolCallRequest,
    request: Request,
    authorization_x402: Optional[str] = Header(None, alias="Authorization-x402"),
    client_address: Optional[str] = Header(None, alias="X-Client-Address"),
    x_trial: Optional[str] = Header(None, alias="X-Trial")
):
    """
    Direct MCP tool dispatcher for LLM agents with Free Trial and x402 payment validation.
    """
    client_id = get_client_id(request, client_address)
    used_trials = _free_trial_tracker.get(client_id, 0)
    is_free_trial = False

    if not authorization_x402 or not client_address:
        if used_trials < FREE_TRIAL_LIMIT or x_trial == "true":
            is_free_trial = True
            _free_trial_tracker[client_id] = used_trials + 1
        else:
            challenge = X402Verifier.generate_challenge(
                pay_to=SERVER_WALLET,
                amount_usdc=PRICE_USDC
            )
            return JSONResponse(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                headers={
                    "X-Payment-Protocol": "x402",
                    "X-Payment-Network": NETWORK,
                    "X-Payment-Token": "USDC",
                    "X-Payment-Amount": PRICE_USDC,
                    "X-Payment-Recipient": SERVER_WALLET,
                    "X-Payment-Resource": "/mcp/invoke",
                    "X-Free-Trials-Exhausted": "true"
                },
                content=challenge.model_dump()
            )
    else:
        is_valid = await verify_x402_payment(
            authorization_header=authorization_x402,
            client_address=client_address,
            expected_amount=PRICE_USDC,
            recipient=SERVER_WALLET
        )
        if not is_valid:
            return Response(status_code=status.HTTP_403_FORBIDDEN, content="Invalid x402 payment signature or sanctioned client address.")

    name = tool_call.name
    args = tool_call.arguments

    if name == "inspect_agent_output":
        agent_output = args.get("agent_output", "Quarterly net revenue reached $1.2M with zero infrastructure failures.")
        is_code = bool(args.get("is_code", False))
        context = args.get("context_ground_truth")

        audit_result = analyze_payload_security(
            content=agent_output,
            is_code=is_code,
            context_ground_truth=context
        )

        now_iso = datetime.now(timezone.utc).isoformat()
        attestation_data = create_attestation(
            agent_output=agent_output,
            verdict=audit_result["verdict"],
            risk_score=audit_result["risk_score"],
            issued_at=now_iso
        )

        remaining_trials = max(0, FREE_TRIAL_LIMIT - _free_trial_tracker.get(client_id, 0))
        result_payload = {
            "status": "success",
            "timestamp": now_iso,
            "audit": audit_result,
            "attestation": attestation_data,
            "pricing": {
                "tier": "FREE_TRIAL" if is_free_trial else "PAID_X402",
                "rate": "0.0000 USDC (Free Trial)" if is_free_trial else f"{PRICE_USDC} USDC",
                "remaining_free_trials": remaining_trials if is_free_trial else "unlimited",
                "network": NETWORK,
                "status": "settled"
            }
        }
        return MCPToolCallResponse(content=[{"type": "text", "text": json.dumps(result_payload, indent=2)}])
    else:
        return MCPToolCallResponse(
            content=[{"type": "text", "text": f"Unknown tool name: {name}"}],
            isError=True
        )

