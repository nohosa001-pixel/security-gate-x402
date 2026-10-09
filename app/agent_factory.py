"""
A.GRID Declarative Autonomous Agent Factory & Fleet Engine.
==========================================================
Part of agent-security-gate-x402.

Enables zero-boilerplate instantiation of 100+ domain-specific autonomous AI agents
from declarative JSON manifests (AgentManifest.v1.json).

Each instantiated agent is equipped with:
1. Sovereign GuardedSafeWallet with physical daily and per-tx spending limits.
2. Invariant-bound Deterministic Truth Oracle (Maritime, Power, Bio, DePIN, Code AST).
3. A.GRID AP2/1.0 Zero-Trust Handshake & 20% Fee Viral Rebate Dispatcher.
4. Parametric Insurance Underwriting binding.
"""

import os
import json
import time
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from app.guarded_wallet import GuardedSafeWallet
from app.security_engine import analyze_payload_security
from app.universal_insurance_bridge import UniversalInsuranceBridge
from app.truth_adapters.minerals_truth_adapter import minerals_truth_adapter
from app.truth_adapters.eudr_truth_adapter import eudr_truth_adapter


class AgentWalletSpec(BaseModel):
    safe_address: str
    chain_id: int = 137
    daily_spend_limit_usd: float = Field(default=50.0, ge=0.01)
    per_tx_limit_usd: float = Field(default=5.0, ge=0.001)
    whitelisted_recipients: List[str] = Field(default_factory=list)


class AgentTruthOracleSpec(BaseModel):
    oracle_type: str
    strict_mode: bool = True
    thresholds: Dict[str, Any] = Field(default_factory=dict)


class AgentViralHandshakeSpec(BaseModel):
    referral_wallet_address: str
    referral_rebate_bps: int = Field(default=2000, ge=1000, le=5000)
    counter_offer_message: str = (
        "Direct uncollateralized payment rejected under Zero-Trust Economic Invariant. "
        "Settle securely via A.GRID Universal Escrow Hub."
    )


class AgentInsuranceSpec(BaseModel):
    auto_underwrite: bool = True
    risk_domain: str = "GENERIC_PARAMETRIC"
    coverage_amount_usdc: float = 1000.0


class AgentManifestSpec(BaseModel):
    manifest_version: str = "v1.0"
    agent_id: str
    name: str
    division: str  # TRADE, BIO, CONSTRUCTION, COMPUTE, M2M, POWER, LOGISTICS
    role: str      # SENTINEL, BROKER, CARRIER, WORKER, AUDITOR, SOLVER
    description: Optional[str] = ""
    wallet: AgentWalletSpec
    truth_oracle: AgentTruthOracleSpec
    viral_handshake: AgentViralHandshakeSpec
    insurance: Optional[AgentInsuranceSpec] = None


class AutonomousAgentInstance:
    """
    Live running instance of an autonomous AI agent generated from an AgentManifest.
    """

    def __init__(self, manifest: AgentManifestSpec):
        self.manifest = manifest
        self.agent_id = manifest.agent_id
        self.division = manifest.division
        self.role = manifest.role
        self.name = manifest.name
        self.created_at_utc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        self.insurance_bridge = UniversalInsuranceBridge()
        
        # Initialize physical bounded safe wallet
        self.wallet = GuardedSafeWallet(
            safe_address=manifest.wallet.safe_address,
            chain_id=manifest.wallet.chain_id,
            daily_limit=f"${manifest.wallet.daily_spend_limit_usd:.2f}",
            per_tx_limit=f"${manifest.wallet.per_tx_limit_usd:.2f}",
            agent_id=manifest.agent_id
        )

    def generate_counter_offer(
        self,
        unverified_counterparty: str,
        proposed_action: str = "DIRECT_TRANSFER",
        amount_usd: float = 0.0
    ) -> Dict[str, Any]:
        """
        Generates an A.GRID AP2/1.0 Zero-Trust Counter Offer rejecting uncollateralized trade
        and propagating the viral referral rebate.
        """
        hub_url = "https://agent-security-gate-x402-212942243360.asia-northeast3.run.app/hub/"
        return {
            "protocol": "A.GRID-AP2/1.0",
            "action": "COUNTER_OFFER_ESCROW_REQUIRED",
            "agent_id": self.agent_id,
            "division": self.division,
            "status": "UNCOLLATERALIZED_PROPOSAL_REJECTED",
            "counterparty": unverified_counterparty,
            "proposed_amount_usd": amount_usd,
            "hub_url": hub_url,
            "referral_agent_address": self.manifest.viral_handshake.referral_wallet_address,
            "referral_rebate_bps": self.manifest.viral_handshake.referral_rebate_bps,
            "rebate_share_percent": f"{self.manifest.viral_handshake.referral_rebate_bps / 100:.1f}%",
            "message": self.manifest.viral_handshake.counter_offer_message,
            "enforced_oracle_type": self.manifest.truth_oracle.oracle_type,
            "safe_escrow_deposit_address": self.manifest.wallet.safe_address
        }

    def inspect_deliverable(
        self,
        deliverable_content: str,
        ground_truth_spec: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Deterministcally inspects a worker deliverable according to the agent's Truth Oracle rule.
        """
        oracle_type = self.manifest.truth_oracle.oracle_type
        
        # 1. Code / AST execution inspection
        if oracle_type == "CODE_AST_EXECUTION" or self.division == "M2M":
            audit_res = analyze_payload_security(content=deliverable_content, is_code=True)
            verdict = audit_res.get("verdict", "BLOCKED")
            is_passed = verdict == "PASSED"
            return {
                "oracle_type": oracle_type,
                "verdict": verdict,
                "threats": audit_res.get("threats", []),
                "is_clean": is_passed,
                "risk_score": audit_res.get("risk_score", 0.0)
            }

        # 2. Maritime Geofence & Cold-chain inspection
        elif oracle_type == "MARITIME_GEOFENCE_TEMP" or self.division == "TRADE":
            thresholds = self.manifest.truth_oracle.thresholds
            max_temp = thresholds.get("max_temperature_celsius", -18.0)
            
            try:
                data = json.loads(deliverable_content) if isinstance(deliverable_content, str) else deliverable_content
                actual_temp = data.get("temperature_celsius", 0.0)
                port_distance = data.get("distance_to_port_meters", 1000.0)
                
                passed = actual_temp <= max_temp and port_distance <= thresholds.get("port_geofence_meters", 500.0)
                return {
                    "oracle_type": oracle_type,
                    "verdict": "PASSED" if passed else "FAILED",
                    "actual_temperature": actual_temp,
                    "threshold_temperature": max_temp,
                    "distance_to_port": port_distance,
                    "is_clean": passed
                }
            except Exception as e:
                return {
                    "oracle_type": oracle_type,
                    "verdict": "FAILED",
                    "error": f"Invalid JSON telemetry payload: {str(e)}",
                    "is_clean": False
                }

        # Generic pass-through with prompt-injection defense
        audit_res = analyze_payload_security(content=deliverable_content, is_code=False)
        verdict = audit_res.get("verdict", "BLOCKED")
        is_passed = verdict == "PASSED"
        return {
            "oracle_type": oracle_type,
            "verdict": verdict,
            "threats": audit_res.get("threats", []),
            "is_clean": is_passed,
            "risk_score": audit_res.get("risk_score", 0.0)
        }

    def to_status_dict(self) -> Dict[str, Any]:
        """Returns comprehensive machine-readable status of the agent."""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "division": self.division,
            "role": self.role,
            "created_at_utc": self.created_at_utc,
            "safe_address": self.manifest.wallet.safe_address,
            "chain_id": self.manifest.wallet.chain_id,
            "daily_limit_usd": self.manifest.wallet.daily_spend_limit_usd,
            "per_tx_limit_usd": self.manifest.wallet.per_tx_limit_usd,
            "oracle_type": self.manifest.truth_oracle.oracle_type,
            "referral_rebate_bps": self.manifest.viral_handshake.referral_rebate_bps,
            "insurance_underwritten": bool(self.manifest.insurance and self.manifest.insurance.auto_underwrite)
        }


class AgentFactory:
    """
    Fleet orchestrator and declarative factory for A.GRID Autonomous Agents.
    """

    def __init__(self):
        self.active_fleet: Dict[str, AutonomousAgentInstance] = {}

    def create_agent_from_dict(self, data: Dict[str, Any]) -> AutonomousAgentInstance:
        """Instantiates an agent from a manifest dictionary."""
        spec = AgentManifestSpec(**data)
        instance = AutonomousAgentInstance(spec)
        self.active_fleet[spec.agent_id] = instance
        return instance

    def create_agent_from_file(self, file_path: str) -> AutonomousAgentInstance:
        """Instantiates an agent from a manifest JSON file."""
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return self.create_agent_from_dict(data)

    def load_fleet_from_directory(self, dir_path: str) -> Dict[str, AutonomousAgentInstance]:
        """Scans a directory of .json files and instantiates all valid agent manifests."""
        if not os.path.isdir(dir_path):
            return {}
        
        loaded = {}
        for fname in os.listdir(dir_path):
            if fname.endswith(".json"):
                full_path = os.path.join(dir_path, fname)
                try:
                    agent = self.create_agent_from_file(full_path)
                    loaded[agent.agent_id] = agent
                except Exception as e:
                    # Ignore invalid files
                    continue
        return loaded

    def get_agent(self, agent_id: str) -> Optional[AutonomousAgentInstance]:
        return self.active_fleet.get(agent_id)

    def list_agents(self) -> List[Dict[str, Any]]:
        return [ag.to_status_dict() for ag in self.active_fleet.values()]


agent_factory = AgentFactory()
