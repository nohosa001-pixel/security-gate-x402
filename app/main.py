"""FastAPI server for Agent Output Security & Hallucination Gate (x402)."""

import os
from datetime import datetime, timezone
from dotenv import load_dotenv
from fastapi import FastAPI, Header, Response, status
from fastapi.middleware.cors import CORSMiddleware
from app.schemas import InspectionRequest, InspectionResponse, AuditReport, AuditAttestation
from app.security_engine import analyze_payload_security
from app.x402_verifier import verify_x402_payment, create_attestation

# Load environment variables from .env if present
load_dotenv()

app = FastAPI(
    title="Agent Output Security & Hallucination Gate (x402)",
    description="Deterministic, ultra-low latency security and hallucination inspection micro-oracle for autonomous agents. Monetized via HTTP 402 on Base ($0.002 USDC).",
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

raw_wallet = os.getenv("SERVER_WALLET_ADDRESS", "0x255F9991233f86B29dB847c8d5b8CB9915e80dCf")
SERVER_WALLET = raw_wallet.strip().split()[0]
PRICE_USDC = os.getenv("PRICE_USDC", "0.002")
NETWORK = os.getenv("NETWORK", "base")


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
        "supported_rails": ["x402-base-usdc"],
        "pricing": {"amount": PRICE_USDC, "currency": "USDC", "network": NETWORK},
        "capabilities": [
            {
                "action": "inspect_agent_output",
                "endpoint": "/api/v1/inspect",
                "description": "Ultra-low latency security, key leak, and factual hallucination validator for 0.002 USDC."
            }
        ],
        "legal": {
            "terms": "/terms",
            "privacy": "/privacy"
        }
    }


@app.post("/api/v1/inspect", response_model=InspectionResponse)
@app.post("/v1/inspect", response_model=InspectionResponse)
async def inspect_payload(
    req: InspectionRequest,
    authorization_x402: str = Header(None, alias="Authorization-x402"),
    client_address: str = Header(None, alias="X-Client-Address")
):
    if not authorization_x402 or not client_address:
        return Response(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            headers={
                "X-Payment-Protocol": "x402",
                "X-Payment-Network": NETWORK,
                "X-Payment-Token": "USDC",
                "X-Payment-Amount": PRICE_USDC,
                "X-Payment-Recipient": SERVER_WALLET,
                "X-Payment-Resource": "/api/v1/inspect"
            },
            content="HTTP 402: Payment of 0.002 USDC required via x402 protocol."
        )

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

    return InspectionResponse(
        status="success",
        timestamp=now_iso,
        audit=audit_obj,
        attestation=AuditAttestation(**attestation_data),
        payment_receipt={
            "amount": PRICE_USDC,
            "currency": "USDC",
            "network": NETWORK,
            "recipient": SERVER_WALLET
        }
    )
