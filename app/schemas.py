"""Pydantic request and response schemas for agent-security-gate-x402."""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class VerdictEnum(str, Enum):
    PASSED = "PASSED"
    FLAGGED = "FLAGGED"
    BLOCKED = "BLOCKED"


class PricingTier(str, Enum):
    FREE_TRIAL = "FREE_TRIAL"
    STANDARD = "STANDARD"
    ENTERPRISE = "ENTERPRISE"
    VAULT_PREFUNDED = "VAULT_PREFUNDED"


class InspectionRequest(BaseModel):
    agent_output: str = Field(
        default="System status: All operational. Quarterly net profit reached $1.2M with zero critical vulnerabilities.",
        description="The LLM or agent output payload to inspect"
    )
    is_code: bool = Field(
        default=False, 
        description="Set to True if payload contains executable Python/shell code"
    )
    context_ground_truth: Optional[str] = Field(
        default=None, 
        description="Original reference context to check for factual accuracy and numerical hallucinations (optional)"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "agent_output": "Our Q3 cloud expenses reached $45,000 across 12 clusters.",
                    "is_code": False,
                    "context_ground_truth": "Financial ledger: Q3 cloud expenses $45,000 for 12 clusters."
                },
                {
                    "agent_output": "import os\nos.system('rm -rf /')",
                    "is_code": True,
                    "context_ground_truth": None
                }
            ]
        }
    }


class NLIReport(BaseModel):
    is_faithful: bool = Field(..., description="Whether output is faithful to the reference ground truth")
    hallucination_score: float = Field(..., description="Hallucination severity score from 0.0 (clean) to 1.0 (heavy hallucination)")
    faithfulness_ratio: float = Field(..., description="Entity & claim grounding ratio from 0.0 to 1.0")
    fabricated_numbers: List[str] = Field(default_factory=list, description="List of unanchored or fabricated numerical claims")
    ungrounded_entities: List[str] = Field(default_factory=list, description="List of named entities absent in ground truth")
    details: Dict[str, Any] = Field(default_factory=dict, description="Detailed NLI / token grounding statistics")


class AuditReport(BaseModel):
    verdict: str = Field(..., description="Audit verdict: 'PASSED', 'FLAGGED', or 'BLOCKED'")
    risk_score: float = Field(..., description="Combined threat & hallucination risk score (0.0 safe to 100.0 critical)")
    is_safe: bool = Field(..., description="True if output is safe to release without blockers")
    threats: List[str] = Field(default_factory=list, description="List of identified security violations and threats")
    nli_verification: Optional[NLIReport] = Field(default=None, description="Factual faithfulness & hallucination report if context was provided")


class AuditAttestation(BaseModel):
    issuer: str = Field(..., description="Gate server issuer address")
    subject_hash: str = Field(..., description="SHA-256 hash of the inspected agent output")
    verdict: str = Field(..., description="Audit verdict: 'PASSED', 'FLAGGED', or 'BLOCKED'")
    risk_score: float = Field(..., description="Risk score assigned to payload")
    issued_at: str = Field(..., description="ISO 8601 UTC timestamp of attestation issuance")
    signature: str = Field(..., description="EIP-191 cryptographic signature from gate server")


class InspectionResponse(BaseModel):
    status: str = Field(default="success", description="Status code or status message")
    timestamp: str = Field(..., description="ISO 8601 UTC timestamp of inspection")
    audit: AuditReport = Field(..., description="Comprehensive security and hallucination audit report")
    attestation: Optional[AuditAttestation] = Field(default=None, description="Cryptographic Proof-of-Safety attestation for downstream agents and smart contracts")
    payment_receipt: Dict[str, Any] = Field(default_factory=dict, description="x402 payment settlement receipt on Polygon")


class PaymentDemand402(BaseModel):
    error: str = Field(default="Payment Required", description="HTTP 402 status description")
    protocol: str = Field(default="x402", description="Payment protocol identifier")
    network: str = Field(default="polygon", description="Settlement blockchain network")
    chain_id: int = Field(default=137, description="Polygon mainnet chain ID (137) or testnet (80002)")
    asset: str = Field(default="0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359", description="USDC contract address on Polygon")
    amount_usdc: str = Field(default="0.002", description="Required payment amount in USD")
    amount_micro_units: int = Field(default=2000, description="Amount in 6-decimal micro USDC units")
    pay_to: str = Field(..., description="Recipient wallet address")
    quote_id: str = Field(..., description="Unique quote/invoice ID")
    expires_at: int = Field(..., description="Unix timestamp expiration of payment quote")
    payment_header: str = Field(default="X-402-Signature", description="Header to pass the signed x402 payment authorization")
    description: str = Field(default="Agent Security & Hallucination Inspection Micro-Oracle Fee ($0.002 USDC on Polygon)", description="Invoice description")


# --- Vault & Enterprise Schemas ---

class VaultDepositRequest(BaseModel):
    agent_address: str = Field(..., description="Ethereum/Polygon checksummed wallet address of the agent")
    amount_usdc: float = Field(..., ge=50.0, description="Amount in USDC to deposit (minimum $50.00 USDC, unlimited upper bound)")
    tx_hash: Optional[str] = Field(default=None, description="Optional on-chain USDC transfer transaction hash")


class BatchInspectionRequest(BaseModel):
    items: List[InspectionRequest] = Field(..., description="List of inspection requests for high-throughput batch audit")


class BatchInspectionResponse(BaseModel):
    status: str = Field(default="success")
    total_count: int
    passed_count: int
    blocked_count: int
    results: List[InspectionResponse]
    payment_receipt: Dict[str, Any] = Field(default_factory=dict)


class VaultDepositResponse(BaseModel):
    status: str = Field(default="success")
    agent_address: str
    balance_usdc: float
    session_key: str = Field(..., description="Zero-latency session key for agent HTTP authorization header 'X-Vault-Key'")
    message: str


class VaultBalanceResponse(BaseModel):
    agent_address: str
    balance_usdc: float
    total_deposited_usdc: float
    total_consumed_usdc: float
    query_count: int
    session_key: str
    last_active_utc: str


class EnterpriseKeyCreateRequest(BaseModel):
    organization_name: str = Field(..., description="Company or Agent DAO Organization Name")
    contact_email: str = Field(..., description="Contact email address")
    tier: PricingTier = Field(default=PricingTier.ENTERPRISE, description="Subscription tier")


class EnterpriseKeyResponse(BaseModel):
    organization_name: str
    api_key: str
    tier: str
    rate_limit_rpm: int
    is_active: bool
    created_at_utc: str


# --- On-Chain EIP-712 Attestation Schemas ---

class OnChainAttestationRequest(BaseModel):
    action_payload: str = Field(..., description="Raw transaction payload, command string, or prompt to attest on-chain")
    risk_score_max: float = Field(default=0.2, ge=0.0, le=1.0, description="Max acceptable risk score threshold")
    chain_id: int = Field(default=137, description="Target EVM Chain ID (137: Polygon, 8453: Base, 42161: Arbitrum)")


class OnChainAttestationResponse(BaseModel):
    status: str = "success"
    action_payload_hash: str = Field(..., description="Keccak256 hash of the action payload (bytes32 hex)")
    risk_score: float
    verdict: str
    is_safe: bool
    chain_id: int
    signer_address: str
    v: int
    r: str
    s: str
    abi_calldata: str = Field(..., description="Raw hex calldata ready to submit directly to SecurityGateConsumer.sol")
    expires_at: int


# --- Multi-Chain Schemas ---

class MultiChainInfo(BaseModel):
    name: str
    chain_id: int
    rpc_url: str
    usdc_address: str
    vault_contract_address: Optional[str] = None
    consumer_contract_address: Optional[str] = None
    safe_guard_address: Optional[str] = None
    credit_oracle_address: Optional[str] = None
    compliance_registry_address: Optional[str] = None
    is_active: bool = True


# --- WebSocket & MCP Schemas ---

class SecurityEventMessage(BaseModel):
    event_type: str = "INSPECTION_AUDIT"
    timestamp: str
    verdict: str
    risk_score: float
    threats_count: int
    is_hallucinated: bool
    caller_ip_masked: str


class MCPToolCallRequest(BaseModel):
    name: str = Field(..., description="MCP Tool name to invoke")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Arguments dictionary for the tool")


class MCPToolCallResponse(BaseModel):
    content: List[Dict[str, Any]] = Field(default_factory=list, description="MCP content array")
    isError: bool = Field(default=False, description="Whether execution resulted in an error")


# --- Escrow & Slashing Schemas ---

class EscrowAuditRequest(BaseModel):
    job_id: int = Field(..., description="Escrow task job ID", examples=[1])
    deliverable: str = Field(..., description="Deliverable text or code from worker agent", examples=["Data analysis complete with 100% accuracy"])
    ground_truth_spec: Optional[str] = Field(None, description="Original job requirement spec to verify factual accuracy", examples=["Analyze revenue ledger for Q3."])
    is_code: bool = Field(False, description="Whether deliverable is executable code")
    chain_id: int = Field(137, description="EVM Chain ID (137 = Polygon)")
    verifying_contract: str = Field("0x0000000000000000000000000000000000000000", description="Deployed AgentEscrow contract address")


# --- Lending Pool Schemas ---

class LoanQuoteRequest(BaseModel):
    agent_address: str = Field(..., description="EVM wallet address of the borrower agent", examples=["0x70997970C51812dc3A010C7d01b50e0d17dc79C8"])
    requested_amount_usdc: float = Field(..., description="Requested uncollateralized loan amount in USDC", examples=[50.0])
    duration_days: int = Field(30, description="Loan duration in days", examples=[14, 30, 60])
    chain_id: int = Field(137, description="EVM Chain ID (137 = Polygon)")


# --- Insurance Pool Schemas ---

class InsuranceQuoteRequest(BaseModel):
    agent_address: str = Field(..., description="EVM wallet address of the insured agent", examples=["0x70997970C51812dc3A010C7d01b50e0d17dc79C8"])
    beneficiary_address: str = Field(..., description="EVM address of policy beneficiary/client", examples=["0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC"])
    coverage_amount_usdc: float = Field(..., description="Requested liability coverage amount in USDC", examples=[500.0])
    duration_days: int = Field(30, description="Insurance policy duration in days", examples=[30])
    chain_id: int = Field(137, description="EVM Chain ID (137 = Polygon)")
    verifying_contract: str = Field("0x0000000000000000000000000000000000000000", description="Deployed AgentInsurancePool contract address")


class InsuranceClaimRequest(BaseModel):
    policy_id: int = Field(..., description="Insurance policy ID", examples=[1])
    agent_address: str = Field(..., description="Faulty agent EVM address", examples=["0x70997970C51812dc3A010C7d01b50e0d17dc79C8"])
    claimant_address: str = Field(..., description="Claimant / beneficiary EVM address", examples=["0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC"])
    claim_amount_usdc: float = Field(..., description="Requested indemnity compensation in USDC", examples=[100.0])
    incident_description: str = Field(..., description="Description of the failure, hallucination, or exploit incident")
    chain_id: int = Field(137, description="EVM Chain ID (137 = Polygon)")
    verifying_contract: str = Field("0x0000000000000000000000000000000000000000", description="Deployed AgentInsurancePool contract address")


# --- Factoring Pool Schemas ---

class FactoringQuoteRequest(BaseModel):
    invoice_id: int = Field(..., description="Invoice / Receivable ID", examples=[101])
    escrow_job_id: int = Field(..., description="Associated AgentEscrow Job ID", examples=[99])
    agent_address: str = Field(..., description="EVM address of the receivable holder agent", examples=["0x70997970C51812dc3A010C7d01b50e0d17dc79C8"])
    face_value_usdc: float = Field(..., description="Face value of the receivable due at milestone", examples=[100.0])
    duration_days: int = Field(30, description="Days remaining until maturity / milestone payment", examples=[14, 30, 60])
    chain_id: int = Field(137, description="EVM Chain ID (137 = Polygon)")
    verifying_contract: str = Field("0x0000000000000000000000000000000000000000", description="Deployed AgentFactoringPool contract address")


class FactoringSettleRequest(BaseModel):
    invoice_id: int = Field(..., description="Invoice / Receivable ID to settle", examples=[101])
    agent_address: str = Field(..., description="EVM address of the receivable holder agent", examples=["0x70997970C51812dc3A010C7d01b50e0d17dc79C8"])
    amount_settled: float = Field(..., description="Full face value amount paid into factoring pool", examples=[100.0])


