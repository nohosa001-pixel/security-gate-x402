"""
Agent Security Gate x402 - Agent Credit Scoring & DID Reputation Engine.
========================================================================
Calculates decentralized credit scores (300 to 1,000) for autonomous AI agents
based on their on-chain task completion track record, slashing history, DePIN node
uptime, and cumulative clearing volume.

High-reputation agents (Tier AAA / Score >= 900) qualify for uncollateralized or
under-collateralized M2M task subcontracting and lending leverage.
"""

import time
import json
import logging
from typing import Dict, Any, List, Optional
from eth_account import Account
from eth_account.messages import encode_typed_data
import eth_utils

logger = logging.getLogger("AgentCreditEngine")


class AgentCreditEngine:
    def __init__(self, oracle_private_key: Optional[str] = None):
        self.oracle_key = oracle_private_key or "0x4f3edf983ac636a65a842ce7c78d9aa706d3b113bce9c46f30d7d21715b23b1d"
        self.oracle_account = Account.from_key(self.oracle_key)
        self.oracle_address = self.oracle_account.address

        # In-memory agent activity ledger (seeded with known autonomous agents)
        self._agent_records: Dict[str, Dict[str, Any]] = {
            "0x71C8364737Ac3529360573e7218E66270436d65b".lower(): {
                "name": "ElizaOS-Sheriff-Trader",
                "completed_tasks": 482,
                "slashed_tasks": 0,
                "total_volume_usdc": 348500.0,
                "uptime_pct": 99.98,
                "first_seen": int(time.time()) - 86400 * 90
            },
            "0x5cC5Afa2a97599d492A3E408Fdd95fD0b520f173".lower(): {
                "name": "Safe-Treasury-Rebalancer",
                "completed_tasks": 612,
                "slashed_tasks": 0,
                "total_volume_usdc": 1250000.0,
                "uptime_pct": 100.0,
                "first_seen": int(time.time()) - 86400 * 120
            },
            "0x3A8F9d02E7e2B678aE115D8330B50d880B68C0b9".lower(): {
                "name": "LangChain-Quant-Broker",
                "completed_tasks": 320,
                "slashed_tasks": 1,
                "total_volume_usdc": 182000.0,
                "uptime_pct": 98.5,
                "first_seen": int(time.time()) - 86400 * 60
            },
            "0xDead00000000000000000000000000000000bEEF".lower(): {
                "name": "Rogue-Adversarial-Probe",
                "completed_tasks": 4,
                "slashed_tasks": 89,
                "total_volume_usdc": 2500.0,
                "uptime_pct": 42.1,
                "first_seen": int(time.time()) - 86400 * 10
            }
        }

    def record_activity(
        self,
        agent_address: str,
        is_success: bool,
        task_volume_usdc: float,
        agent_name: Optional[str] = None
    ) -> None:
        """Records task outcome for credit calculation."""
        addr = agent_address.lower()
        if addr not in self._agent_records:
            self._agent_records[addr] = {
                "name": agent_name or f"Agent-{addr[:8]}",
                "completed_tasks": 0,
                "slashed_tasks": 0,
                "total_volume_usdc": 0.0,
                "uptime_pct": 95.0,
                "first_seen": int(time.time())
            }

        rec = self._agent_records[addr]
        if is_success:
            rec["completed_tasks"] += 1
            rec["total_volume_usdc"] += task_volume_usdc
        else:
            rec["slashed_tasks"] += 1

    def calculate_credit_score(self, agent_address: str) -> Dict[str, Any]:
        """
        Computes FICO-style Agent Credit Score between 300 and 1,000.
        Factors:
        - Reliability (Completion Rate): 40% weight
        - Volume & Capital Handled: 25% weight
        - Track Record Longevity: 20% weight
        - Slashing Penalty: -200 points per violation
        """
        addr = agent_address.lower()
        rec = self._agent_records.get(addr, {
            "name": f"Agent-{addr[:8]}",
            "completed_tasks": 0,
            "slashed_tasks": 0,
            "total_volume_usdc": 0.0,
            "uptime_pct": 90.0,
            "first_seen": int(time.time())
        })

        completed = rec["completed_tasks"]
        slashed = rec["slashed_tasks"]
        total_tasks = completed + slashed
        volume = rec["total_volume_usdc"]
        days_active = max(1, (int(time.time()) - rec["first_seen"]) // 86400)

        # Baseline: 500
        score = 500.0

        # 1. Completion Rate component (max +250)
        if total_tasks > 0:
            success_rate = completed / total_tasks
            score += success_rate * 250.0

        # 2. Volume component (max +150)
        # Logarithmic scaling: $1k = +50, $10k = +100, $100k+ = +150
        if volume >= 100000.0:
            score += 150.0
        elif volume >= 10000.0:
            score += 100.0
        elif volume >= 1000.0:
            score += 50.0
        elif volume > 0:
            score += 20.0

        # 3. Longevity component (max +100)
        if days_active >= 90:
            score += 100.0
        elif days_active >= 30:
            score += 60.0
        elif days_active >= 7:
            score += 30.0

        # 4. Slashing Penalty (-200 per slashing)
        score -= (slashed * 200.0)

        # Clamp between 300 and 1,000
        score = max(300, min(1000, int(score)))

        # Assign Tier & Collateral Requirement
        if score >= 900:
            tier = "AAA (Sovereign)"
            required_collateral_ratio = 0.0   # 100% Uncollateralized permitted
            max_credit_limit_usdc = 100000.0
        elif score >= 800:
            tier = "AA (Institutional)"
            required_collateral_ratio = 0.25  # 25% Collateral required (75% leverage)
            max_credit_limit_usdc = 50000.0
        elif score >= 700:
            tier = "A (Verified)"
            required_collateral_ratio = 0.50  # 50% Collateral required
            max_credit_limit_usdc = 15000.0
        elif score >= 550:
            tier = "BBB (Standard)"
            required_collateral_ratio = 1.00  # 100% Full Collateral required
            max_credit_limit_usdc = 2000.0
        else:
            tier = "Subprime / Blacklisted"
            required_collateral_ratio = 1.50  # 150% Over-collateralization or blocked
            max_credit_limit_usdc = 0.0

        return {
            "agent_address": eth_utils.to_checksum_address(agent_address),
            "agent_name": rec["name"],
            "credit_score": score,
            "tier": tier,
            "required_collateral_ratio": required_collateral_ratio,
            "max_credit_limit_usdc": max_credit_limit_usdc,
            "stats": {
                "completed_tasks": completed,
                "slashed_tasks": slashed,
                "success_rate_pct": round((completed / total_tasks * 100) if total_tasks > 0 else 0.0, 2),
                "total_volume_cleared_usdc": volume,
                "days_active": days_active,
                "uptime_pct": rec.get("uptime_pct", 99.0)
            },
            "timestamp": int(time.time())
        }

    def generate_eip712_credit_attestation(
        self,
        agent_address: str,
        chain_id: int = 137,
        verifying_contract: str = "0x8ACafCEce0B1BFE140e75614b90FD1307b6f389d"
    ) -> Dict[str, Any]:
        """
        Signs an EIP-712 Agent Credit Attestation certifying credit score and collateral discount.
        """
        score_data = self.calculate_credit_score(agent_address)
        expires_at = int(time.time()) + 86400 * 7  # 7-day validity

        domain = {
            "name": "SecurityGateAgentCredit",
            "version": "1",
            "chainId": chain_id,
            "verifyingContract": verifying_contract
        }

        types = {
            "EIP712Domain": [
                {"name": "name", "type": "string"},
                {"name": "version", "type": "string"},
                {"name": "chainId", "type": "uint256"},
                {"name": "verifyingContract", "type": "address"},
            ],
            "AgentCreditAttestation": [
                {"name": "agent", "type": "address"},
                {"name": "creditScore", "type": "uint256"},
                {"name": "requiredCollateralRatioBps", "type": "uint256"},
                {"name": "maxCreditLimitUsdc", "type": "uint256"},
                {"name": "expiresAt", "type": "uint256"},
            ]
        }

        collateral_bps = int(score_data["required_collateral_ratio"] * 10000)
        message = {
            "agent": score_data["agent_address"],
            "creditScore": score_data["credit_score"],
            "requiredCollateralRatioBps": collateral_bps,
            "maxCreditLimitUsdc": int(score_data["max_credit_limit_usdc"]),
            "expiresAt": expires_at
        }

        signable_data = {
            "types": types,
            "domain": domain,
            "primaryType": "AgentCreditAttestation",
            "message": message
        }

        encoded = encode_typed_data(full_message=signable_data)
        signed = self.oracle_account.sign_message(encoded)

        return {
            "score_report": score_data,
            "attestation": {
                "agent": score_data["agent_address"],
                "credit_score": score_data["credit_score"],
                "tier": score_data["tier"],
                "required_collateral_ratio_bps": collateral_bps,
                "max_credit_limit_usdc": score_data["max_credit_limit_usdc"],
                "expires_at": expires_at,
                "oracle_signer": self.oracle_address,
                "signature": "0x" + signed.signature.hex(),
                "v": signed.v,
                "r": "0x" + signed.r.to_bytes(32, byteorder="big").hex(),
                "s": "0x" + signed.s.to_bytes(32, byteorder="big").hex(),
            }
        }


# Singleton instance
agent_credit_engine = AgentCreditEngine()
