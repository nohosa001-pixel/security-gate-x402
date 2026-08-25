"""Pydantic request and response schemas for agent-security-gate-x402."""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class VerdictEnum(str, Enum):
    PASSED = "PASSED"
    FLAGGED = "FLAGGED"
    BLOCKED = "BLOCKED"


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
    payment_receipt: Dict[str, Any] = Field(default_factory=dict, description="x402 payment settlement receipt on Base")


class PaymentDemand402(BaseModel):
    error: str = Field(default="Payment Required", description="HTTP 402 status description")
    protocol: str = Field(default="x402", description="Payment protocol identifier")
    network: str = Field(default="base", description="Settlement blockchain network")
    chain_id: int = Field(default=8453, description="Base mainnet chain ID (8453) or testnet (84532)")
    asset: str = Field(default="0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913", description="USDC contract address on Base")
    amount_usdc: str = Field(default="0.002", description="Required payment amount in USD")
    amount_micro_units: int = Field(default=2000, description="Amount in 6-decimal micro USDC units")
    pay_to: str = Field(..., description="Recipient wallet address")
    quote_id: str = Field(..., description="Unique quote/invoice ID")
    expires_at: int = Field(..., description="Unix timestamp expiration of payment quote")
    payment_header: str = Field(default="X-402-Signature", description="Header to pass the signed x402 payment authorization")
    description: str = Field(default="Agent Security & Hallucination Inspection Micro-Oracle Fee ($0.002 USDC on Base)", description="Invoice description")


class MCPToolCallRequest(BaseModel):
    name: str = Field(..., description="MCP Tool name to invoke")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Arguments dictionary for the tool")


class MCPToolCallResponse(BaseModel):
    content: List[Dict[str, Any]] = Field(default_factory=list, description="MCP content array")
    isError: bool = Field(default=False, description="Whether execution resulted in an error")

