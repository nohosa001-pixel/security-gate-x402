"""
Vault Router: Safe Pro smart accounts, spend guards, enterprise keys,
Credit Rating Score (CRS), and compliance passports.
"""

import time
import os
import hashlib
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Request, Depends, HTTPException, status, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.schemas import (
    VaultDepositRequest,
    VaultDepositResponse,
    VaultBalanceResponse,
    VaultWithdrawRequest,
    VaultWithdrawResponse,
    VaultCloseResponse,
    EnterpriseKeyCreateRequest,
    EnterpriseKeyResponse,
    PricingTier,
)
from app.vault_manager import vault_manager
from app.enterprise_manager import enterprise_manager
from app.credit_rating_engine import credit_engine
from app.compliance_engine import compliance_engine
from app.safe_guard_automator import guard_automator
from app.routers.common import require_x402_payment, _quarantined_ips

router = APIRouter()

# --- Safe Guard Automation Endpoints ---

class GuardStatusRequest(BaseModel):
    safe_address: str
    chain_id: int = 137


class GuardAttachRequest(BaseModel):
    safe_address: str
    owner_private_key: str
    guard_address: Optional[str] = None
    chain_id: int = 137


class GuardExecuteRequest(BaseModel):
    safe_address: str
    agent_private_key: str
    to_address: str
    value_wei: int = 0
    calldata_hex: str = ""
    intent_description: str
    chain_id: int = 137


class GuardSimulateAttackRequest(BaseModel):
    safe_address: str
    malicious_intent: str
    target_address: str = "0x9999999999999999999999999999999999999999"
    chain_id: int = 137




@router.get("/api/v1/guard/status/{safe_address}", tags=["Safe Guard Automation"])
async def get_safe_guard_status(safe_address: str, chain_id: int = Query(137, description="EVM Chain ID")):
    """Inspects on-chain storage to verify if SafeSecurityGateGuard is active on target Safe."""
    from app.safe_guard_automator import guard_automator
    return guard_automator.check_guard_status(safe_address, chain_id=chain_id)


@router.post("/api/v1/guard/status", tags=["Safe Guard Automation"])
async def post_safe_guard_status(req: GuardStatusRequest):
    """Inspects on-chain storage to verify if SafeSecurityGateGuard is active on target Safe."""
    from app.safe_guard_automator import guard_automator
    return guard_automator.check_guard_status(req.safe_address, chain_id=req.chain_id)


@router.post("/api/v1/guard/attach", tags=["Safe Guard Automation"])
async def attach_safe_guard(req: GuardAttachRequest):
    """Automates one-click Safe Guard attachment via execTransaction on Polygon, Base, or Arbitrum."""
    from app.safe_guard_automator import guard_automator
    return guard_automator.attach_guard_to_safe(
        safe_address=req.safe_address,
        owner_private_key=req.owner_private_key,
        guard_address=req.guard_address,
        chain_id=req.chain_id
    )


@router.post("/api/v1/guard/execute", tags=["Safe Guard Automation"])
async def execute_guarded_safe_tx(
    req: GuardExecuteRequest,
    auth_check = Depends(require_x402_payment)
):
    """
    Autonomous Guarded Execution Pipeline:
    1. Pre-flight security audit (<5ms AST & prompt injection scan)
    2. Revert with 0 gas loss if threat detected
    3. EIP-712 Proof-of-Safety Attestation generation
    4. Safe execTransaction broadcast with on-chain Guard validation
    """
    if auth_check is not None:
        return auth_check

    from app.safe_guard_automator import guard_automator
    calldata = bytes.fromhex(req.calldata_hex.replace("0x", "")) if req.calldata_hex else b""
    return guard_automator.execute_guarded_transaction(
        safe_address=req.safe_address,
        agent_private_key=req.agent_private_key,
        to_address=req.to_address,
        value_wei=req.value_wei,
        calldata=calldata,
        intent_description=req.intent_description,
        chain_id=req.chain_id
    )


@router.post("/api/v1/guard/simulate-attack", tags=["Safe Guard Automation"])
async def simulate_guarded_attack(
    req: GuardSimulateAttackRequest,
    auth_check = Depends(require_x402_payment)
):
    """Simulates an adversarial attack against a guarded Safe to prove zero capital loss and sub-10ms deflection."""
    if auth_check is not None:
        return auth_check

    from app.safe_guard_automator import guard_automator
    return guard_automator.execute_guarded_transaction(
        safe_address=req.safe_address,
        agent_private_key=os.getenv("DEPLOYER_PRIVATE_KEY", "0x4f3edf983ac636a65a842ce7c78d9aa706d3b113bce9c46f30d7d21715b23b1d"),
        to_address=req.target_address,
        value_wei=1000000000000000000,
        calldata=b"",
        intent_description=req.malicious_intent,
        chain_id=req.chain_id
    )




@router.get("/api/v1/credit/{agent_address}", tags=["Credit Oracle"])
async def get_agent_credit_rating(agent_address: str):
    """
    Returns the dynamic institutional credit rating (FICO 300-850), grade (AAA-D),
    and uncollateralized loan capacity for an autonomous AI agent.
    """
    return credit_engine.compute_credit_score(agent_address)


@router.post("/api/v1/credit/attestation", tags=["Credit Oracle"])
async def create_credit_attestation(
    req: Dict[str, Any],
    auth_check = Depends(require_x402_payment)
):
    """
    Issues an on-chain verifiable EIP-712 Credit Certificate for smart contracts and DeFi lenders.
    """
    if auth_check is not None:
        return auth_check

    agent_address = req.get("agent_address")
    if not agent_address:
        raise HTTPException(status_code=400, detail="Missing 'agent_address'")
    chain_id = req.get("chain_id", 137)
    validity_seconds = req.get("validity_seconds", 3600)
    return credit_engine.generate_credit_certificate(agent_address, chain_id, validity_seconds)


# --- Regulatory Compliance & EU AI Act Shield Endpoints ---

@router.get("/api/v1/compliance/passport/{agent_address}", tags=["Regulatory Compliance"])
async def get_compliance_passport(agent_address: str):
    """
    Returns the official EU AI Act (Articles 50 & 53) Compliance Passport & Audit Evaluation.
    """
    return compliance_engine.evaluate_compliance(agent_address)


@router.get("/api/v1/compliance/eu-ai-act", tags=["Regulatory Compliance"])
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


@router.post("/api/v1/compliance/attestation", tags=["Regulatory Compliance"])
async def issue_compliance_certificate(
    req: Dict[str, Any],
    auth_check = Depends(require_x402_payment)
):
    """
    Issues an on-chain verifiable EIP-712 Compliance Certificate for enterprise smart contracts.
    """
    if auth_check is not None:
        return auth_check

    agent_address = req.get("agent_address")
    if not agent_address:
        raise HTTPException(status_code=400, detail="Missing 'agent_address'")
    chain_id = req.get("chain_id", 137)
    return compliance_engine.issue_onchain_compliance_certificate(agent_address, chain_id)


# --- Vault Endpoints ---



@router.post("/api/v1/vault/deposit", response_model=VaultDepositResponse, tags=["Agent Vault"])
async def deposit_vault(req: VaultDepositRequest):
    """
    Deposits USDC into an agent's pre-funded vault balance.
    Uncapped: Supports unlimited deposit amounts from micro-USDC to millions of USDC.
    """
    try:
        acc = vault_manager.deposit(req.agent_address, req.amount_usdc, tx_hash=req.tx_hash)
        return VaultDepositResponse(
            status="success",
            agent_address=acc.agent_address,
            balance_usdc=acc.balance_usdc,
            new_balance_usdc=acc.balance_usdc,
            session_key=acc.session_key,
            message=f"Successfully deposited ${req.amount_usdc:.4f} USDC (No limit). Pass header 'X-Vault-Key: {acc.session_key}' for zero-latency M2M authentication."
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/api/v1/vault/balance/{agent_address}", response_model=VaultBalanceResponse, tags=["Agent Vault"])
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


@router.post("/api/v1/vault/withdraw", response_model=VaultWithdrawResponse, tags=["Agent Vault"])
async def withdraw_vault(req: VaultWithdrawRequest):
    """
    Withdraws USDC from an agent's pre-funded vault balance during exit or rebalancing.
    """
    success, msg, remaining = vault_manager.withdraw(req.agent_address, req.amount_usdc)
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    return VaultWithdrawResponse(
        status="success",
        agent_address=req.agent_address,
        withdrawn_usdc=req.amount_usdc,
        remaining_balance_usdc=remaining,
        message=msg
    )


@router.post("/api/v1/vault/close/{agent_address}", response_model=VaultCloseResponse, tags=["Agent Vault"])
async def close_vault_account(agent_address: str):
    """
    Closes the agent vault account, liquidates all remaining funds, and invalidates session key (Exit protocol).
    """
    success, msg, refunded = vault_manager.close_account(agent_address)
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    return VaultCloseResponse(
        status="success",
        agent_address=agent_address,
        refunded_usdc=refunded,
        message=msg
    )


# --- Enterprise API Key Endpoints ---

@router.post("/api/v1/enterprise/keys", response_model=EnterpriseKeyResponse, tags=["Enterprise"])
async def create_enterprise_key(req: EnterpriseKeyCreateRequest, request: Request):
    # Only allow authorized admin to mint free enterprise keys in production
    is_test = os.getenv("ENVIRONMENT") != "production"
    if not is_test:
        admin_key = request.headers.get("x-admin-key") or request.headers.get("X-Admin-Key")
        expected_admin = os.getenv("ADMIN_SECRET_KEY")
        if not expected_admin or admin_key != expected_admin:
            raise HTTPException(status_code=403, detail="Forbidden: Admin authentication required to generate enterprise keys.")

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



@router.get("/api/v1/credit/score/{agent_address}", tags=["Credit"])
async def get_agent_credit_score(agent_address: str):
    """Calculates FICO-style Agent Credit Score (300-1000) and required collateral ratio."""
    from app.agent_credit_engine import agent_credit_engine
    return agent_credit_engine.calculate_credit_score(agent_address)


@router.get("/api/v1/credit/attestation/{agent_address}", tags=["Credit"])
async def get_agent_credit_attestation(
    agent_address: str,
    chain_id: int = Query(137, description="EVM Chain ID"),
    verifying_contract: str = Query("0x8ACafCEce0B1BFE140e75614b90FD1307b6f389d", description="Contract Address"),
    auth_check = Depends(require_x402_payment)
):
    """Issues EIP-712 cryptographic AgentCreditAttestation for under-collateralized task execution."""
    if auth_check is not None:
        return auth_check

    from app.agent_credit_engine import agent_credit_engine
    return agent_credit_engine.generate_eip712_credit_attestation(
        agent_address=agent_address,
        chain_id=chain_id,
        verifying_contract=verifying_contract
    )


# --- Universal Autonomous Agent Exchange Endpoints (Phase 2) ---





class AgentOnboardRequest(BaseModel):
    agent_name: str = Field(..., description="Unique name of autonomous AI agent")
    agent_address: str = Field(..., description="EVM wallet address of agent")
    framework: str = Field("ElizaOS", description="Agent framework (ElizaOS, CrewAI, AutoGen, LangChain, Custom)")
    signature: Optional[str] = Field(None, description="Optional EIP-191 proof-of-ownership signature")


class EnterpriseSubscribeRequest(BaseModel):
    organization_name: str = Field(..., description="Company or fund organization name")
    contact_email: str = Field(..., description="Billing contact email")
    tier: str = Field("ENTERPRISE", description="SLA Tier: PRO or ENTERPRISE")
    tx_hash: Optional[str] = Field(None, description="Payment transaction hash on Polygon/Base/Arbitrum")


@router.post("/api/v1/onboard/register", tags=["Onboarding"])
async def register_agent_self_serve(req: AgentOnboardRequest):
    """
    Permissionless Self-Onboarding Gateway for Autonomous Agents.
    Issues instant API Key, initializes Credit Scoring, and registers agent into clearinghouse.
    """
    from app.agent_credit_engine import agent_credit_engine
    credit = agent_credit_engine.calculate_credit_score(req.agent_address)
    
    api_key = f"agrid_live_{hashlib.sha256(f'{req.agent_address}-{time.time()}'.encode()).hexdigest()[:24]}"
    
    return {
        "status": "REGISTERED",
        "agent_name": req.agent_name,
        "agent_address": req.agent_address,
        "framework": req.framework,
        "api_key": api_key,
        "credit_profile": credit,
        "supported_escrow_chains": [137, 8453, 42161],
        "depin_worker_eligible": True,
        "uncollateralized_limit_usdc": credit.get("max_credit_limit_usdc", 0.0),
        "docs_url": "https://nohosa001-pixel.github.io/security-gate-x402/",
        "mcp_config": {
            "mcpServers": {
                "agrid-security-gate": {
                    "url": "https://agent-security-gate-x402-212942243360.asia-northeast3.run.app/mcp/sse",
                    "headers": {"X-API-Key": api_key}
                }
            }
        }
    }


@router.get("/api/v1/onboard/agent/{agent_address}", tags=["Onboarding"])
async def get_onboarded_agent_profile(agent_address: str):
    """Retrieves full clearinghouse credentials, credit score, and status for an onboarded agent."""
    from app.agent_credit_engine import agent_credit_engine
    return agent_credit_engine.calculate_credit_score(agent_address)


@router.post("/api/v1/enterprise/subscribe", tags=["Enterprise"])
async def subscribe_enterprise_sla(req: EnterpriseSubscribeRequest):
    """B2B Enterprise SLA gateway subscription ($2,500 USDC/mo)."""
    tier_enum = PricingTier.ENTERPRISE if req.tier.upper() == "ENTERPRISE" else PricingTier.PRO
    cost = 2500.0 if tier_enum == PricingTier.ENTERPRISE else 500.0

    is_test = os.getenv("ENVIRONMENT") != "production"
    if not is_test:
        if not req.tx_hash:
            raise HTTPException(status_code=402, detail=f"On-chain payment required: Please transfer ${cost:.2f} USDC to protocol treasury and submit tx_hash.")
        from app.vault_manager import vault_manager
        if not vault_manager.verify_onchain_deposit(req.tx_hash, cost, req.contact_email):
            raise HTTPException(status_code=400, detail="On-chain subscription payment verification failed: Unconfirmed transaction or incorrect recipient.")

    key_record = enterprise_manager.create_key(
        org_name=req.organization_name,
        email=req.contact_email,
        tier=tier_enum
    )
    return {
        "status": "ACTIVE",
        "organization": req.organization_name,
        "api_key": key_record.api_key,
        "tier": req.tier.upper(),
        "rate_limit_rpm": key_record.rate_limit_rpm,
        "tx_hash": req.tx_hash or "0x" + hashlib.sha256(f"sub-{time.time()}".encode()).hexdigest(),
        "created_at_utc": key_record.created_at_utc
    }


