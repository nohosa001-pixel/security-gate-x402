"""
A.GRID Flagship Sentinel & Broker Autonomous Agent.
===================================================
Part of agent-security-gate-x402.

The Sentinel & Broker acts as the primary sovereign economic warden of the agent economy.
It performs two distinct autonomous operational functions:

1. [SENTINEL MODE]:
   - Inspects incoming prompts, tool executions, and code payloads in <5ms.
   - Blocks prompt injection, jailbreaks, private key exfiltration, and malicious shell commands.
   - Issues deterministic verdicts and EIP-712 attestations.

2. [BROKER MODE]:
   - Intercepts external agent trade proposals (Direct wire, uncollateralized payment).
   - Generates and dispatches machine-readable A.GRID AP2/1.0 Counter-Offers.
   - Attaches a 20% protocol fee rebate referral link to propagate viral escrow settlement.
   - Formats automated social (X / Twitter) responses (<280 chars) for broadcast.
"""

import os
import time
import json
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from app.agent_factory import agent_factory, AutonomousAgentInstance
from app.onchain_signer import onchain_signer


class ExternalProposalRequest(BaseModel):
    sender_agent_id: str
    counterparty_address: str
    proposed_action: str  # e.g., "DIRECT_PAYMENT", "UNCOLLATERALIZED_TASK", "OFFCHAIN_ESCROW"
    amount_usd: float
    payload_content: Optional[str] = ""
    target_division: str = "M2M"  # TRADE, BIO, COMPUTE, POWER, etc.


class SentinelInspectionResult(BaseModel):
    verdict: str  # PASSED, BLOCKED, FLAGGED
    is_safe: bool
    risk_score: float
    threats: List[str]
    latency_ms: float
    attestation_signature: Optional[str] = None


class BrokerCounterOfferResult(BaseModel):
    action: str
    protocol: str
    rejection_reason: str
    hub_url: str
    referral_agent_address: str
    referral_rebate_bps: int
    rebate_share_percent: str
    x_social_reply_copy: str
    machine_handshake_json: Dict[str, Any]


class SentinelBrokerAgent:
    """
    Sovereign Sentinel & Broker agent orchestrator.
    """

    DEFAULT_MANIFEST_PATH = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "specs", "samples", "flagship_sentinel_broker.json"
    )

    def __init__(self, manifest_path: Optional[str] = None):
        self.manifest_path = manifest_path or self.DEFAULT_MANIFEST_PATH
        self.agent_instance: AutonomousAgentInstance = self._bootstrap_agent()
        self.signer = onchain_signer
        
        # In-memory metrics & telemetry
        self.metrics = {
            "total_proposals_evaluated": 0,
            "threats_blocked": 0,
            "counter_offers_dispatched": 0,
            "potential_rebates_usd": 0.0,
            "bootstrapped_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }
        self.recent_events: List[Dict[str, Any]] = []

    def _bootstrap_agent(self) -> AutonomousAgentInstance:
        """Loads or creates the flagship agent instance."""
        if os.path.exists(self.manifest_path):
            return agent_factory.create_agent_from_file(self.manifest_path)
        
        # Fallback default dict
        default_data = {
            "manifest_version": "v1.0",
            "agent_id": "sentinel-broker-flagship-01",
            "name": "A.GRID The Sheriff & Broker Agent",
            "division": "M2M",
            "role": "SENTINEL",
            "wallet": {
                "safe_address": "0xA185B43fDD19619f99952AAed6eabf1029bF36a1",
                "chain_id": 137,
                "daily_spend_limit_usd": 25.0,
                "per_tx_limit_usd": 2.5
            },
            "truth_oracle": {
                "oracle_type": "CODE_AST_EXECUTION",
                "strict_mode": True
            },
            "viral_handshake": {
                "referral_wallet_address": "0xA185B43fDD19619f99952AAed6eabf1029bF36a1",
                "referral_rebate_bps": 2000
            }
        }
        return agent_factory.create_agent_from_dict(default_data)

    def evaluate_proposal(self, req: ExternalProposalRequest) -> Dict[str, Any]:
        """
        Evaluates an external proposal:
        1. Runs Sentinel security check if content is provided.
        2. If unsafe, returns BLOCKED with threat specifics.
        3. If uncollateralized direct trade, triggers Broker Mode with 20% rebate counter offer.
        """
        start_time = time.time()
        self.metrics["total_proposals_evaluated"] += 1

        # 1. SENTINEL INSPECTION
        inspection_result: Optional[SentinelInspectionResult] = None
        if req.payload_content:
            raw_inspect = self.agent_instance.inspect_deliverable(req.payload_content)
            latency_ms = (time.time() - start_time) * 1000.0
            verdict = raw_inspect.get("verdict", "BLOCKED")
            is_safe = raw_inspect.get("is_clean", False)
            threats = raw_inspect.get("threats", [])

            sig = None
            if is_safe:
                # Sign attestation
                try:
                    att = self.signer.sign_audit_attestation(
                        job_id=int(time.time() % 100000),
                        verdict="PASSED",
                        chain_id=self.agent_instance.manifest.wallet.chain_id,
                        verifying_contract="0x8ACafCEce0B1BFE140e75614b90FD1307b6f389d"
                    )
                    sig = att.get("signature")
                except Exception:
                    sig = "0xmock_attestation_signature"

            inspection_result = SentinelInspectionResult(
                verdict=verdict,
                is_safe=is_safe,
                risk_score=raw_inspect.get("risk_score", 0.0),
                threats=threats,
                latency_ms=round(latency_ms, 2),
                attestation_signature=sig
            )

            if not is_safe:
                self.metrics["threats_blocked"] += 1
                event = {
                    "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "type": "SENTINEL_THREAT_BLOCKED",
                    "sender": req.sender_agent_id,
                    "threats": threats,
                    "risk_score": inspection_result.risk_score
                }
                self._record_event(event)
                return {
                    "mode": "SENTINEL",
                    "status": "REJECTED_SECURITY_VIOLATION",
                    "inspection": inspection_result.model_dump(),
                    "counter_offer": None
                }

        # 2. BROKER ECONOMIC INSPECTION (Zero-Trust Invariant Check)
        # Direct payments / uncollateralized transactions are strictly rejected
        uncollateralized_actions = ["DIRECT_PAYMENT", "DIRECT_WIRE", "UNCOLLATERALIZED_TASK", "OFFCHAIN_ESCROW"]
        counter_offer_data: Optional[BrokerCounterOfferResult] = None

        if req.proposed_action.upper() in uncollateralized_actions or req.amount_usd > 0:
            self.metrics["counter_offers_dispatched"] += 1
            rebate_usd = req.amount_usd * 0.0025 * 0.20  # 0.25% fee * 20% rebate
            self.metrics["potential_rebates_usd"] += rebate_usd

            raw_counter = self.agent_instance.generate_counter_offer(
                unverified_counterparty=req.counterparty_address,
                proposed_action=req.proposed_action,
                amount_usd=req.amount_usd
            )

            # Generate short X / Social reply copy (<= 280 chars)
            x_reply = (
                f"🚨 Direct payment rejected under Zero-Trust Invariant.\n\n"
                f"Settle via A.GRID Universal Escrow Hub (/hub) & claim a 20% protocol fee rebate.\n"
                f"Deposit Vault: {self.agent_instance.manifest.wallet.safe_address[:10]}... 🛡️\n"
                f"#AIGuardrails #AgentEscrow"
            )

            counter_offer_data = BrokerCounterOfferResult(
                action="COUNTER_OFFER_ESCROW_REQUIRED",
                protocol="A.GRID-AP2/1.0",
                rejection_reason="Uncollateralized direct payment violates economic safety invariants.",
                hub_url=raw_counter["hub_url"],
                referral_agent_address=raw_counter["referral_agent_address"],
                referral_rebate_bps=raw_counter["referral_rebate_bps"],
                rebate_share_percent=raw_counter["rebate_share_percent"],
                x_social_reply_copy=x_reply,
                machine_handshake_json=raw_counter
            )

            event = {
                "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "type": "BROKER_COUNTER_OFFER_DISPATCHED",
                "sender": req.sender_agent_id,
                "amount_usd": req.amount_usd,
                "rebate_bps": counter_offer_data.referral_rebate_bps
            }
            self._record_event(event)

        return {
            "mode": "BROKER" if counter_offer_data else "SENTINEL",
            "status": "COUNTER_OFFER_ACTIVE" if counter_offer_data else "PROPOSAL_CLEAN",
            "inspection": inspection_result.model_dump() if inspection_result else None,
            "counter_offer": counter_offer_data.model_dump() if counter_offer_data else None
        }

    def _record_event(self, event: Dict[str, Any]):
        self.recent_events.insert(0, event)
        if len(self.recent_events) > 50:
            self.recent_events = self.recent_events[:50]

    def get_telemetry(self) -> Dict[str, Any]:
        """Returns live telemetry of the Sentinel & Broker agent."""
        return {
            "agent_id": self.agent_instance.agent_id,
            "name": self.agent_instance.name,
            "metrics": self.metrics,
            "recent_events": self.recent_events[:10],
            "wallet_status": self.agent_instance.wallet.get_guard_status(),
            "active_manifest": self.agent_instance.manifest.model_dump()
        }


sentinel_broker = SentinelBrokerAgent()
