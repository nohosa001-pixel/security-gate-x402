"""Pydantic request and response schemas for agent-security-gate-x402."""

from enum import Enum
from typing import Any, Dict, List, Optional, Union
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


class IncidentDetail(BaseModel):
    category: str = Field(..., description="Threat category: PROMPT_INJECTION, SECRET_LEAK, DANGEROUS_AST_CALL, CODE_SYNTAX_ERROR, FACTUAL_HALLUCINATION")
    severity: str = Field(default="HIGH", description="Severity level: 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'")
    reason: str = Field(..., description="Human-readable plain English explanation of the threat")
    matched_snippet: Optional[str] = Field(default=None, description="Contextual excerpt of the offending token or pattern")
    action_taken: str = Field(default="TOOL_CALL_BLOCKED", description="Recommended or enforced mitigation action")


class AuditReport(BaseModel):
    verdict: str = Field(..., description="Audit verdict: 'PASSED', 'FLAGGED', or 'BLOCKED'")
    risk_score: float = Field(..., description="Combined threat & hallucination risk score (0.0 safe to 100.0 critical)")
    is_safe: bool = Field(..., description="True if output is safe to release without blockers")
    threats: List[str] = Field(default_factory=list, description="List of identified security violations and threats")
    incidents: List[IncidentDetail] = Field(default_factory=list, description="Structured, explainable incident details for team observability & SIEM")
    cli_summary: Optional[str] = Field(default=None, description="Human-readable one-line terminal/Slack log summary")
    nli_verification: Optional[NLIReport] = Field(default=None, description="Factual faithfulness & hallucination report if context was provided")


class AuditAttestation(BaseModel):
    issuer: str = Field(..., description="Gate server issuer address")
    subject_hash: str = Field(..., description="SHA-256 hash of the inspected agent output")
    verdict: str = Field(..., description="Audit verdict: 'PASSED', 'FLAGGED', or 'BLOCKED'")
    risk_score: float = Field(..., description="Risk score assigned to payload")
    issued_at: str = Field(..., description="ISO 8601 UTC timestamp of attestation issuance")
    signature: str = Field(..., description="EIP-191 cryptographic signature from gate server")


class AuditProof(BaseModel):
    proof_hash: str = Field(..., description="Deterministic SHA-256 fingerprint of the audit record snapshot")
    signature: str = Field(..., description="EIP-191 cryptographic signature from the Sheriff gate server")
    issuer: str = Field(..., description="Gate server Ethereum address that issued this proof")
    terms: str = Field(default="ZERO_LIABILITY_AS_IS_PROVENANCE_V1", description="Legal terms binding the inspection snapshot. See /api/v1/terms.")
    terms_url: str = Field(default="/api/v1/terms", description="Canonical endpoint serving the full legal terms specification")
    timestamp: int = Field(..., description="Unix epoch timestamp when audit proof was sealed")
    audit_record: Dict[str, Any] = Field(default_factory=dict, description="Immutable snapshot of inspection metadata")


class InspectionResponse(BaseModel):
    status: str = Field(default="success", description="Status code or status message")
    timestamp: str = Field(..., description="ISO 8601 UTC timestamp of inspection")
    audit: AuditReport = Field(..., description="Comprehensive security and hallucination audit report")
    attestation: Optional[AuditAttestation] = Field(default=None, description="Cryptographic Proof-of-Safety attestation for downstream agents and smart contracts")
    audit_proof: Optional[AuditProof] = Field(default=None, description="Zero-Liability provenance and cryptographic audit proof")
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
    new_balance_usdc: Optional[float] = None
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


class VaultWithdrawRequest(BaseModel):
    agent_address: str = Field(..., description="Ethereum/Polygon wallet address of the agent or session key")
    amount_usdc: float = Field(..., gt=0.0, description="Amount in USDC to withdraw from vault")
    destination_address: Optional[str] = Field(default=None, description="Optional destination address (defaults to agent address)")


class VaultWithdrawResponse(BaseModel):
    status: str = Field(default="success")
    agent_address: str
    withdrawn_usdc: float
    remaining_balance_usdc: float
    message: str


class VaultCloseResponse(BaseModel):
    status: str = Field(default="success")
    agent_address: str
    refunded_usdc: float
    message: str


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
    chain_id: Union[int, str]
    network_slug: Optional[str] = None
    rpc_url: str
    usdc_address: str
    explorer_url: Optional[str] = None
    vault_contract_address: Optional[str] = None
    consumer_contract_address: Optional[str] = None
    safe_guard_address: Optional[str] = None
    credit_oracle_address: Optional[str] = None
    compliance_registry_address: Optional[str] = None
    universal_escrow_address: Optional[str] = None
    truth_adapter_address: Optional[str] = None
    is_active: bool = True


class SolanaTruthAttestationRequest(BaseModel):
    job_id_hex: str
    domain: int
    truth_hash_hex: str
    recipients_hash_hex: str
    validity_seconds: int = 3600


class SolanaTruthAttestationResponse(BaseModel):
    chain: str = "solana-mainnet"
    chain_id: int = 501
    oracle_signer_pubkey: str
    signature_b58: str
    signature_hex: str
    expires_at: int
    domain: int
    job_id_hex: str
    truth_hash_hex: str
    recipients_hash_hex: str


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


class M2MEscrowSettleRequest(BaseModel):
    job_id: int = Field(..., description="Escrow task job ID", examples=[1])
    client_address: str = Field(..., description="Payer agent wallet address", examples=["0xAlice11111111111111111111111111111111111"])
    worker_address: str = Field(..., description="Worker agent wallet address", examples=["0xBob2222222222222222222222222222222222222"])
    payout_usdc: float = Field(..., gt=0.0, description="Agreed payout amount in USDC", examples=[5.0])
    deliverable: str = Field(..., description="Worker task deliverable to audit and settle", examples=["Task finished successfully."])
    ground_truth_spec: Optional[str] = Field(None, description="Job requirement specification to test fidelity")
    is_code: bool = Field(False, description="Whether deliverable is executable code")
    chain_id: int = Field(137, description="EVM Chain ID (137 = Polygon)")
    referral_agent_address: Optional[str] = Field(None, description="Optional wallet address of referring agent to receive 20% protocol fee rebate")


# --- Universal Modular Truth Adapter Schemas ---

class SplitRecipientItem(BaseModel):
    recipient: str = Field(..., description="EVM address of beneficiary (laborer, supplier, research team)")
    amount: float = Field(..., gt=0.0, description="Disbursal amount in USDC")


class MaritimeTruthRequest(BaseModel):
    job_id: str = Field(..., description="Escrow task unique job ID", examples=["job_maritime_101"])
    current_gps: List[float] = Field(..., min_length=2, max_length=2, description="[Latitude, Longitude] of vessel", examples=[[35.1035, 129.0410]])
    destination_port_gps: List[float] = Field(..., min_length=2, max_length=2, description="[Latitude, Longitude] of destination port", examples=[[35.1028, 129.0403]])
    temperature_timeseries_celsius: List[float] = Field(..., min_length=1, description="Container cold-chain temperature logs", examples=[[-20.1, -19.8, -20.2]])
    rfid_tag: str = Field(..., description="Automated unloading port RFID tag scanned", examples=["RFID-BUSAN-GATE-4402"])
    expected_rfid_tag: str = Field(..., description="Expected contract RFID tag", examples=["RFID-BUSAN-GATE-4402"])
    max_geofence_radius_meters: float = Field(500.0, description="Max allowed distance to port in meters")
    chain_id: int = Field(137, description="EVM Chain ID (137 = Polygon)")
    verifying_contract: str = Field("0x5555555555555555555555555555555555555555", description="UniversalEscrowCore deployed address")


class BioZkTruthRequest(BaseModel):
    job_id: str = Field(..., description="Escrow task unique job ID", examples=["job_bio_genomics_201"])
    genomic_merkle_root: str = Field(..., description="Cryptographic Merkle Root of genomic/molecular sequence", examples=["0x" + "f" * 64])
    expected_merkle_root: str = Field(..., description="Contract expected Merkle Root", examples=["0x" + "f" * 64])
    binding_affinity_kd_nm: float = Field(..., gt=0.0, description="Sub-nanomolar binding affinity Kd (lower is tighter)", examples=[3.85])
    kd_threshold_nm: float = Field(10.0, description="Maximum acceptable Kd threshold in nM")
    zk_proof_hex: Optional[str] = Field(None, description="Hex-encoded ZK-SNARK proof")
    tee_enclave_id: Optional[str] = Field("INTEL_SGX_ENCLAVE_V3", description="Confidential compute TEE enclave ID")
    chain_id: int = Field(137, description="EVM Chain ID (137 = Polygon)")
    verifying_contract: str = Field("0x5555555555555555555555555555555555555555", description="UniversalEscrowCore deployed address")


class BuildDroneTruthRequest(BaseModel):
    job_id: str = Field(..., description="Escrow task unique job ID", examples=["job_construction_301"])
    drone_lidar_volume_m3: float = Field(..., gt=0.0, description="Drone 3D LiDAR point-cloud measured concrete volume in m³", examples=[4960.0])
    bim_target_volume_m3: float = Field(..., gt=0.0, description="Target design volume from 3D BIM model in m³", examples=[5000.0])
    concrete_strength_samples_mpa: List[float] = Field(..., min_length=1, description="IoT embedded sensor compressive strength readings in MPa", examples=[[28.5, 30.2, 29.0, 31.4]])
    min_volumetric_ratio: float = Field(0.985, description="Minimum acceptable volumetric match ratio (0.985 = 98.5%)")
    min_concrete_strength_mpa: float = Field(24.0, description="Minimum compressive strength in MPa")
    bim_spec_hash: Optional[str] = Field(None, description="BIM architectural CAD model specification hash")
    chain_id: int = Field(137, description="EVM Chain ID (137 = Polygon)")
    verifying_contract: str = Field("0x5555555555555555555555555555555555555555", description="UniversalEscrowCore deployed address")


class EudrTruthRequest(BaseModel):
    job_id: str = Field(..., description="Escrow task unique job ID", examples=["job_eudr_timber_401"])
    commodity: str = Field(..., description="EUDR Annex I commodity (wood, rubber, palm_oil, soy, coffee, cocoa, cattle)", examples=["timber"])
    country_code: str = Field(..., description="ISO 3166-1 alpha-2 production country", examples=["BR"])
    polygon_coordinates: List[List[float]] = Field(..., min_length=3, description="List of [latitude, longitude] plot polygon vertices", examples=[[[-3.12, -60.02], [-3.12, -60.01], [-3.13, -60.01], [-3.13, -60.02]]])
    dds_reference_id: str = Field(..., description="EU Due Diligence Statement registry ID", examples=["EU-DDS-2026-BR-99482"])
    deforestation_detected: bool = Field(False, description="Flag indicating if deforestation was detected on/after cutoff date (must be False)")
    legal_harvest_verified: bool = Field(True, description="Proof of compliance with local harvest & land tenure legislation (must be True)")
    satellite_cutoff_date: str = Field("2020-12-31", description="EUDR baseline cutoff date")
    chain_id: int = Field(137, description="EVM Chain ID (137 = Polygon)")
    verifying_contract: str = Field("0x5555555555555555555555555555555555555555", description="UniversalEscrowCore deployed address")


class MineralsTruthRequest(BaseModel):
    job_id: str = Field(..., description="Escrow task unique job ID", examples=["job_minerals_cobalt_501"])
    mineral_type: str = Field(..., description="Regulated 3TG or battery critical mineral (tin, tantalum, tungsten, gold, cobalt, lithium, nickel)", examples=["cobalt"])
    smelter_id: str = Field(..., description="RMI or officially audited smelter/refiner CID", examples=["CID001842"])
    smelter_audit_status: str = Field("CONFORMANT", description="Smelter audit status (CONFORMANT, ACTIVE, CERTIFIED)", examples=["CONFORMANT"])
    mine_country_code: str = Field(..., description="ISO 3166-1 alpha-2 mine country of origin", examples=["CD"])
    chain_of_custody_verified: bool = Field(True, description="Verified bag-and-tag / mass-balance custody chain (must be True)")
    child_labor_free: bool = Field(True, description="Zero-tolerance human rights & child labor freedom attestation (must be True)")
    conflict_region: bool = Field(False, description="Whether the mine is in a Conflict-Affected and High-Risk Area (CAHRA)")
    enhanced_due_diligence: bool = Field(True, description="Enhanced OECD due diligence mitigation satisfied for CAHRA areas")
    chain_id: int = Field(137, description="EVM Chain ID (137 = Polygon)")
    verifying_contract: str = Field("0x5555555555555555555555555555555555555555", description="UniversalEscrowCore deployed address")


class UniversalEscrowSettleRequest(BaseModel):
    job_id: str = Field(..., description="Universal escrow task unique job ID", examples=["job_bridge_milestone_4"])
    domain: int = Field(..., description="Domain enum (0=Maritime, 1=Bio, 2=Construction, 3=EUDR_FOREST, 4=CONFLICT_MINERALS)")
    recipients: List[SplitRecipientItem] = Field(..., min_length=1, description="List of direct split beneficiaries and amounts")
    truth_payload: str = Field(..., description="Truth payload text or hex proof data")
    attestation: Dict[str, Any] = Field(..., description="EIP-712 Attestation signed by Oracle")
    chain_id: int = Field(137, description="EVM Chain ID (137 = Polygon)")
    verifying_contract: str = Field("0x5555555555555555555555555555555555555555", description="UniversalEscrowCore deployed address")


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


# --- Treasury Vault & Hedge Fund Schemas ---

class StrategyAuthRequest(BaseModel):
    strategy_id: int = Field(..., description="Unique Strategy execution ID", examples=[1])
    agent_address: str = Field(..., description="EVM address of the AI Fund Manager Agent", examples=["0x70997970C51812dc3A010C7d01b50e0d17dc79C8"])
    target_protocol: str = Field(..., description="Whitelisted target contract address to allocate funds to", examples=["0x6418f408cFf03F862D7691f01fAb00a895E6aB93"])
    max_allocation_usdc: float = Field(..., description="Maximum USDC allocation approved for this trade", examples=[10000.0])
    max_slippage_bps: int = Field(50, description="Max permitted slippage in basis points (50 = 0.5%)", examples=[50, 100])
    strategy_rationale: str = Field(..., description="Reasoning and prompt context for trade execution", examples=["Allocate capital to Stage 4 Factoring Pool for 24% APY yield."])
    chain_id: int = Field(137, description="EVM Chain ID (137 = Polygon)")
    verifying_contract: str = Field("0x0000000000000000000000000000000000000000", description="Deployed AgentTreasuryVault contract address")


class PerformanceSplitRequest(BaseModel):
    gross_profit_usdc: float = Field(..., description="Gross profit in USDC generated by the strategy", examples=[200.0])


# --- Legal Terms & Zero-Liability Schemas ---

class TermsOfServiceResponse(BaseModel):
    service: str = Field(default="Agent Security Gate x402", description="Service name")
    terms_identifier: str = Field(default="ZERO_LIABILITY_AS_IS_PROVENANCE_V1", description="Canonical identifier of the governing terms")
    version: str = Field(default="1.0.0", description="Terms version")
    effective_date: str = Field(default="2026-09-10", description="Effective date in YYYY-MM-DD format")
    title: str = Field(default="Terms of Service & Legal Disclaimer (ZERO_LIABILITY_AS_IS_PROVENANCE_V1)", description="Document title")
    terms: Dict[str, str] = Field(
        default_factory=lambda: {
            "as_is_disclaimer": "The service is provided 'as is' without warranty of any kind.",
            "limitation_of_liability": "In no event shall the authors or copyright holders be liable for any claim or damages."
        },
        description="Backward-compatible terms dictionary"
    )
    summary: Dict[str, str] = Field(..., description="Key legal principles and limitation summaries")
    liability_cap_usd: float = Field(default=50.0, description="Strict aggregate liability cap in USD")
    canonical_terms_sha256: str = Field(..., description="SHA-256 hash of the canonical TERMS_OF_SERVICE.md file")
    full_text_url: str = Field(default="https://github.com/nohosa001-pixel/security-gate-x402/blob/main/TERMS_OF_SERVICE.md", description="URL to complete markdown terms")
    status: str = Field(default="active", description="Terms status")


# --- Universal Factoring & Parametric Insurance Schemas ---

class UniversalFactoringQuoteRequest(BaseModel):
    job_id: str = Field(..., description="Active escrow job ID in UniversalEscrowCore", examples=["job_eudr_timber_401"])
    agent_address: str = Field(..., description="EVM address of the worker agent holding the future receivable", examples=["0x70997970C51812dc3A010C7d01b50e0d17dc79C8"])
    face_value_usdc: float = Field(..., ge=1.0, description="Gross amount of receivable to factor", examples=[10000.0])
    duration_days: int = Field(default=14, ge=1, le=365, description="Expected days until truth oracle unlocks escrow", examples=[14])
    chain_id: int = Field(default=137, description="Chain ID (137 = Polygon, 8453 = Base, 42161 = Arbitrum)")
    verifying_contract: Optional[str] = Field(None, description="AgentFactoringPool address (defaults to deployed address)")


class UniversalFactoringExecuteRequest(BaseModel):
    invoice_id: int = Field(..., description="Invoice ID generated by the quote", examples=[1001])
    job_id: str = Field(..., description="Associated Universal Escrow job ID", examples=["job_eudr_timber_401"])
    agent_address: str = Field(..., description="Worker agent address", examples=["0x70997970C51812dc3A010C7d01b50e0d17dc79C8"])
    face_value_usdc: float = Field(..., description="Gross face value in USDC", examples=[10000.0])
    advance_amount_usdc: float = Field(..., description="Advance liquidity in USDC", examples=[9800.0])
    chain_id: int = Field(default=137, description="Chain ID")


class UniversalParametricQuoteRequest(BaseModel):
    job_id: str = Field(..., description="Active escrow job ID in UniversalEscrowCore", examples=["job_maritime_freight_801"])
    agent_address: str = Field(..., description="Agent purchasing insurance", examples=["0x70997970C51812dc3A010C7d01b50e0d17dc79C8"])
    beneficiary_address: str = Field(..., description="Recipient of insurance payout upon incident", examples=["0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC"])
    coverage_amount_usdc: float = Field(..., ge=10.0, description="Maximum coverage amount in USDC", examples=[5000.0])
    risk_domain: str = Field(default="CUSTOMS_DELAY", description="Domain risk type (CUSTOMS_DELAY, PORT_CONGESTION, SATELLITE_OUTAGE, HARDWARE_FAULT)", examples=["CUSTOMS_DELAY"])
    duration_days: int = Field(default=30, ge=1, le=180, description="Policy validity duration in days", examples=[30])
    chain_id: int = Field(default=137, description="Chain ID")


class UniversalParametricTriggerRequest(BaseModel):
    job_id: str = Field(..., description="Insured Universal Escrow job ID", examples=["job_maritime_freight_801"])
    policy_id: int = Field(..., description="Active policy ID in AgentInsurancePool", examples=[1])
    claimant_address: str = Field(..., description="Address claiming compensation", examples=["0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC"])
    trigger_event: str = Field(..., description="Incident event type (CUSTOMS_DELAY, PORT_CONGESTION, SATELLITE_OUTAGE, HARDWARE_FAULT)", examples=["CUSTOMS_DELAY"])
    metric_value: float = Field(..., description="Quantified metric trigger value (e.g. 52.5 hours of delay)", examples=[52.5])
    threshold_value: float = Field(..., description="Contractual threshold value (e.g. 48.0 hours)", examples=[48.0])
    incident_proof_hash: str = Field(..., description="SHA-256 or keccak256 proof of outage / satellite cloud cover", examples=["0x1234abcd"])
    chain_id: int = Field(default=137, description="Chain ID")


# --- Phase 2: Synthetic Data Vault & Micro-Licensing Schemas ---

class DataAssetRegisterRequest(BaseModel):
    asset_id: str = Field(..., description="Unique dataset or model weight identifier", examples=["asset_cleanweb_eu_grid_01"])
    provider_address: str = Field(..., description="EVM address of data provider/seller", examples=["0x70997970C51812dc3A010C7d01b50e0d17dc79C8"])
    asset_type: str = Field(..., description="CLEANWEB_DATASET, BIOPHARMA_MOLECULAR, AI_WEIGHT_LORA, or SYNTHETIC_CLINICAL", examples=["CLEANWEB_DATASET"])
    ciphertext_hash: str = Field(..., description="0x-prefixed sha256 or keccak256 hash of encrypted ciphertext", examples=["0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"])
    key_commitment: str = Field(..., description="0x-prefixed 32-byte keccak256 commitment of raw decryption key", examples=["0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890"])
    price_usdc: float = Field(..., ge=0.0, description="Purchase price in USDC", examples=[250.0])
    zk_proof: Optional[str] = Field(None, description="Optional SNARK proof of data validity/binding affinity", examples=["0x0000000000000000000000000000000000000000000000000000000000000000"])
    merkle_root: Optional[str] = Field(None, description="Optional Merkle root of data chunks", examples=["0x0000000000000000000000000000000000000000000000000000000000000000"])
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Custom metadata tags")


class DataVaultSwapCreateRequest(BaseModel):
    order_id: str = Field(..., description="Unique atomic swap order ID", examples=["order_swap_cw_901"])
    asset_id: str = Field(..., description="Registered data asset ID", examples=["asset_cleanweb_eu_grid_01"])
    buyer_address: str = Field(..., description="EVM address of the buyer agent", examples=["0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC"])
    chain_id: int = Field(default=137, description="Chain ID for escrow lock")
    timelock_seconds: int = Field(default=3600, ge=60, le=604800, description="Timelock expiry in seconds")


class DataVaultSwapExecuteRequest(BaseModel):
    order_id: str = Field(..., description="Atomic swap order ID to unlock", examples=["order_swap_cw_901"])
    provider_address: str = Field(..., description="Data provider address revealing the key", examples=["0x70997970C51812dc3A010C7d01b50e0d17dc79C8"])
    decryption_key_hex: str = Field(..., description="Raw decryption key in hex format whose keccak256 matches key_commitment", examples=["0x4a5b6c..."])
    chain_id: int = Field(default=137, description="Chain ID")


class MicroLicenseTariffRegisterRequest(BaseModel):
    asset_id: str = Field(..., description="Asset or API ID", examples=["api_bio_smiles_lookup"])
    provider_address: str = Field(..., description="EVM address of license provider", examples=["0x70997970C51812dc3A010C7d01b50e0d17dc79C8"])
    rate_type: str = Field(..., description="PER_QUERY, PER_WEIGHT_MB, or PER_INFERENCE_STEP", examples=["PER_QUERY"])
    price_per_unit_usdc: float = Field(..., gt=0.0, description="Price per unit in USDC", examples=[0.0005])
    min_units: int = Field(default=1, ge=1, description="Minimum units per order")
    max_units_per_order: int = Field(default=1_000_000, ge=1, description="Maximum units per order")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Model/endpoint metadata")


class MicroLicensePurchaseRequest(BaseModel):
    asset_id: str = Field(..., description="Asset identifier", examples=["api_bio_smiles_lookup"])
    consumer_address: str = Field(..., description="Consumer EVM address", examples=["0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC"])
    units_requested: int = Field(..., ge=1, description="Quantity of units to license", examples=[1000])
    chain_id: int = Field(default=137, description="Chain ID")
    validity_seconds: int = Field(default=86400, ge=60, description="Validity period in seconds")


class MicroLicenseMeterRequest(BaseModel):
    token_id: str = Field(..., description="Active capability token ID (e.g. MLT-...)", examples=["MLT-1234567890abcdef"])
    units_consumed: int = Field(..., ge=1, description="Number of units consumed in this execution call", examples=[1])


# --- Phase 3: Energy Grid & Autonomous Fleet PoD Schemas ---

class PowerContractRegisterRequest(BaseModel):
    contract_id: str = Field(..., description="Unique PPA contract identifier", examples=["ppa_grid_caiso_001"])
    provider_address: str = Field(..., description="EVM address of power generator / VPP operator", examples=["0x70997970C51812dc3A010C7d01b50e0d17dc79C8"])
    consumer_address: str = Field(..., description="EVM address of consumer data center / GPU cluster", examples=["0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC"])
    rate_per_kwh_usdc: float = Field(..., gt=0.0, description="Base tariff in USDC per kWh", examples=[0.075])
    grid_zone: str = Field(..., description="Regional power grid zone", examples=["US-CAL-CAISO", "EU-DE-LU"])
    meter_device_id: str = Field(..., description="Bound hardware Smart Meter device ID", examples=["METER-ION-9000-01"])
    is_renewable: bool = Field(default=True, description="Whether power includes renewable attributes")
    rec_rate_multiplier: float = Field(default=1.0, ge=0.5, le=5.0, description="Rate multiplier for verified REC green power")
    max_kwh_limit: float = Field(default=10_000_000.0, description="Maximum contractual kWh limit")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Metadata tags")


class PowerStreamMeterRequest(BaseModel):
    contract_id: str = Field(..., description="Active PPA contract ID", examples=["ppa_grid_caiso_001"])
    kwh_consumed: float = Field(..., gt=0.0, description="Electricity consumed in this interval in kWh", examples=[125.4])
    meter_device_id: str = Field(..., description="Hardware Smart Meter device ID", examples=["METER-ION-9000-01"])
    voltage_v: float = Field(..., description="Real-time voltage reading in Volts", examples=[480.2])
    frequency_hz: float = Field(..., description="Real-time grid frequency reading in Hertz", examples=[60.02])
    meter_signature: str = Field(..., description="Cryptographic signature from smart meter secure enclave", examples=["0x..."])
    rec_certificate_hash: Optional[str] = Field(None, description="Optional hash of Renewable Energy Certificate", examples=["0xabcdef123456..."])
    chain_id: int = Field(default=137, description="Chain ID")


class FleetMissionRegisterRequest(BaseModel):
    mission_id: str = Field(..., description="Unique delivery mission identifier", examples=["mission_truck_rot_to_ams_01"])
    shipper_address: str = Field(..., description="EVM address of the shipper agent locking freight", examples=["0x70997970C51812dc3A010C7d01b50e0d17dc79C8"])
    carrier_address: str = Field(..., description="EVM address of the autonomous carrier agent", examples=["0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC"])
    cargo_description: str = Field(..., description="Description of cargo payload", examples=["GPU Server Racks / NVIDIA H100"])
    freight_amount_usdc: float = Field(..., gt=0.0, description="Freight escrow amount in USDC", examples=[350.0])
    target_lat: float = Field(..., ge=-90.0, le=90.0, description="Target destination latitude", examples=[52.3676])
    target_lon: float = Field(..., ge=-180.0, le=180.0, description="Target destination longitude", examples=[4.9041])
    eseal_pubkey_hash: str = Field(..., description="Hash of physical Electronic Seal hardware public key", examples=["0x..."])
    geofence_radius_meters: float = Field(default=500.0, ge=10.0, le=50000.0, description="Geofence arrival tolerance radius in meters")
    timelock_seconds: int = Field(default=86400, ge=300, description="Mission timelock in seconds")
    max_temp_celsius: Optional[float] = Field(None, description="Maximum cold chain temperature threshold")
    min_temp_celsius: Optional[float] = Field(None, description="Minimum cold chain temperature threshold")
    chain_id: int = Field(default=137, description="Chain ID")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Metadata tags")


class FleetDeliveryVerifyRequest(BaseModel):
    mission_id: str = Field(..., description="Delivery mission ID", examples=["mission_truck_rot_to_ams_01"])
    carrier_address: str = Field(..., description="Autonomous carrier address submitting PoD", examples=["0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC"])
    delivery_lat: float = Field(..., ge=-90.0, le=90.0, description="Actual GNSS delivery latitude", examples=[52.3677])
    delivery_lon: float = Field(..., ge=-180.0, le=180.0, description="Actual GNSS delivery longitude", examples=[4.9042])
    eseal_tamper_flag: bool = Field(..., description="False if seal is intact; True if physical tampering occurred")
    eseal_signature: str = Field(..., description="Cryptographic signature from E-Seal hardware", examples=["0x..."])
    ambient_temp_celsius: Optional[float] = Field(None, description="Ambient cargo hold temperature reading")
    chain_id: int = Field(default=137, description="Chain ID")


class ShellInspectionRequest(BaseModel):
    command: str = Field(..., description="Shell command or pipeline to inspect", examples=["ls -la /app"])


class ZkTLSVerificationRequest(BaseModel):
    server_domain: str = Field(..., description="Origin HTTPS server domain", examples=["api.binance.com"])
    http_method: str = Field(default="GET", description="HTTP method", examples=["GET"])
    revealed_data: Dict[str, Any] = Field(..., description="Revealed JSON key-values from the web response", examples=[{"symbol": "ETHUSDC", "price": "3450.50"}])
    notary_signature: str = Field(..., description="Notary cryptographic signature", examples=["0x..."])
    session_timestamp: int = Field(..., description="Session timestamp in epoch seconds")
    session_commitment_hash: str = Field(..., description="Cryptographic hash commitment of session TLS transcript")
    max_age_seconds: int = Field(default=3600, description="Maximum allowed freshness window in seconds")







