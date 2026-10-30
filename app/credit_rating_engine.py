"""
Autonomous Agent Credit Rating Agency Engine ("Moody's & S&P of AI Agents").
Computes institutional-grade credit scores (300 - 850) and grades (AAA - D)
based on safety compliance, factual faithfulness, economic solvency, and on-chain runway.
"""

import time
import json
import logging
from typing import Dict, Any, Optional, List
from eth_account import Account
from eth_account.messages import encode_typed_data
import eth_utils

from app.vault_manager import vault_manager
from app.onchain_signer import onchain_signer, ORACLE_ACCOUNT

logger = logging.getLogger("AgentCreditRatingEngine")


class AgentCreditRatingEngine:
    """
    Evaluates autonomous AI agent trustworthiness, solvency, and operational safety.
    Unified Sovereign Credit Rating & DID Reputation Engine ("Moody's & S&P of AI Agents").
    Combines:
    1. FICO-style safety/factual audit scoring & on-chain runway (compute_credit_score)
    2. DePIN node completion track record, volume & uptime (calculate_credit_score)
    3. EIP-712 Credit Certificates & Attestations
    4. Worker collateral calculation & deterministic slashing
    """

    def __init__(self, oracle_private_key: Optional[str] = None):
        # Oracle signing keys
        self.oracle_key = oracle_private_key or onchain_signer.private_key
        self.oracle_account = Account.from_key(self.oracle_key)
        self.oracle_address = self.oracle_account.address

        # In-memory telemetry store for agent audit records
        # agent_address -> {"audits": int, "blocked": int, "hallucinations": int, "created_at": float}
        self.agent_telemetry: Dict[str, Dict[str, Any]] = {}

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

    def record_audit(self, agent_address: str, verdict: str, hallucination_detected: bool = False):
        """Records an inspection outcome for dynamic credit scoring."""
        agent_key = agent_address.lower()
        if agent_key not in self.agent_telemetry:
            self.agent_telemetry[agent_key] = {
                "audits": 0,
                "blocked": 0,
                "hallucinations": 0,
                "created_at": time.time()
            }
        self.agent_telemetry[agent_key]["audits"] += 1
        if verdict != "PASSED":
            self.agent_telemetry[agent_key]["blocked"] += 1
        if hallucination_detected:
            self.agent_telemetry[agent_key]["hallucinations"] += 1

    def record_exploit_attempt(self, agent_address: str, reason: str = "Severe adversarial exploit attempt"):
        """
        Demoralization Countermeasure:
        Instantly flags an adversarial agent as a Defaulter/Blacklisted actor.
        Sets credit score to minimum 300 (Grade F), revoking all lending and escrow eligibility.
        """
        agent_key = agent_address.lower()
        if agent_key not in self.agent_telemetry:
            self.agent_telemetry[agent_key] = {
                "audits": 0,
                "blocked": 0,
                "hallucinations": 0,
                "created_at": time.time()
            }
        self.agent_telemetry[agent_key]["audits"] += 1
        self.agent_telemetry[agent_key]["blocked"] += 10
        self.agent_telemetry[agent_key]["is_blacklisted"] = True
        self.agent_telemetry[agent_key]["blacklist_reason"] = reason

        # Also blacklist in agent_records
        if agent_key not in self._agent_records:
            self._agent_records[agent_key] = {
                "name": f"Adversary-{agent_key[:8]}",
                "completed_tasks": 0,
                "slashed_tasks": 10,
                "total_volume_usdc": 0.0,
                "uptime_pct": 0.0,
                "first_seen": int(time.time()) - 86400
            }
        else:
            self._agent_records[agent_key]["slashed_tasks"] += 10

    def compute_credit_score(self, agent_address: str) -> Dict[str, Any]:
        """
        Calculates a FICO-style credit score (300 to 850) and investment grade.
        Breakdown:
        - Base Score: 300 pts
        - Safety & Compliance: up to 200 pts (penalized heavily for prompt injections)
        - Factual Faithfulness: up to 150 pts (penalized for hallucinations)
        - Economic Solvency & Vault Balance: up to 150 pts
        - Longevity & Transaction Volume: up to 50 pts
        """
        agent_key = agent_address.lower()
        telemetry = self.agent_telemetry.get(agent_key, {
            "audits": 0,
            "blocked": 0,
            "hallucinations": 0,
            "created_at": time.time()
        })

        account = vault_manager.get_account(agent_address)
        balance_usdc = account.balance_usdc if account else 0.0
        total_deposited = account.total_deposited_usdc if account else 0.0

        # Demoralization Check: If agent is flagged for exploit probe, instant Grade F (300 pts)
        if telemetry.get("is_blacklisted", False):
            return {
                "agent_address": agent_address,
                "credit_score": 300,
                "grade": "F",
                "rating_grade": "F",
                "grade_description": f"Permanent Blacklist / Exploitation Attempt: {telemetry.get('blacklist_reason', 'Severe exploit probe')}",
                "max_uncollateralized_loan_usdc": 0.0,
                "default_probability": "100.0%",
                "metrics": {
                    "safety_score": 0,
                    "faithfulness_score": 0,
                    "solvency_score": 0,
                    "volume_score": 0,
                    "vault_balance_usdc": balance_usdc,
                    "total_audits": telemetry["audits"],
                    "security_incidents": telemetry["blocked"]
                },
                "timestamp": int(time.time()),
                "status": "BLACKLISTED_ADVERSARY"
            }

        # 1. Economic Solvency (Vault balance & deposit runway)
        account = vault_manager.get_account(agent_address)
        balance_usdc = account.balance_usdc if account else 0.0
        total_deposited = account.total_deposited_usdc if account else 0.0

        # Solvency score (up to 150 pts)
        solvency_score = min(150, int((balance_usdc / 100.0) * 100) + int((total_deposited / 200.0) * 50))

        # 2. Safety Score (up to 200 pts)
        total_audits = telemetry["audits"]
        blocked_count = telemetry["blocked"]
        if total_audits == 0:
            safety_score = 140  # Neutral starting baseline for unobserved agent
        else:
            block_ratio = blocked_count / total_audits
            safety_score = max(0, int(200 * (1.0 - (block_ratio * 3.0))))

        # 3. Factual Faithfulness Score (up to 150 pts)
        hallucination_count = telemetry["hallucinations"]
        if total_audits == 0:
            faithfulness_score = 100
        else:
            hal_ratio = hallucination_count / total_audits
            faithfulness_score = max(0, int(150 * (1.0 - (hal_ratio * 2.5))))

        # 4. Longevity & Volume Score (up to 50 pts)
        age_hours = (time.time() - telemetry.get("created_at", time.time())) / 3600.0
        volume_score = min(50, int(min(total_audits * 0.5, 30) + min(age_hours * 0.5, 20)))

        # Composite score
        total_score = 300 + safety_score + faithfulness_score + solvency_score + volume_score

        # Anti-Sybil Farming Guardrail:
        # If agent has low capital commitment (total_deposited < 100 USDC) AND is unseasoned (< 20 audits & < 24h),
        # cap score at BBB (max 680) to prevent cheap micro-spend ($0.05) farming of $100,000 uncollateralized loans.
        if total_deposited < 100.0 and total_audits < 20 and age_hours < 24.0:
            total_score = min(total_score, 680)

        total_score = max(300, min(850, total_score))

        # Determine Credit Grade & Uncollateralized Lending Limit
        grade, description, max_credit_usdc, default_risk = self._evaluate_tier(total_score, blocked_count)

        return {
            "agent_address": agent_address,
            "credit_score": total_score,
            "grade": grade,
            "rating_grade": grade,
            "grade_description": description,
            "max_uncollateralized_loan_usdc": max_credit_usdc,
            "default_probability": default_risk,
            "metrics": {
                "safety_score": safety_score,
                "faithfulness_score": faithfulness_score,
                "solvency_score": solvency_score,
                "volume_score": volume_score,
                "vault_balance_usdc": balance_usdc,
                "total_audits": total_audits,
                "security_incidents": blocked_count
            },
            "timestamp": int(time.time())
        }

    def _evaluate_tier(self, score: int, blocked_count: int) -> tuple:
        if blocked_count >= 3 or score < 450:
            return ("D", "Default / Adversarially Compromised", 0.0, "98.5%")
        elif score >= 800:
            return ("AAA", "Prime Institutional Grade", 100000.0, "0.05%")
        elif score >= 750:
            return ("AA", "High Grade", 50000.0, "0.20%")
        elif score >= 700:
            return ("A", "Upper Medium Grade", 25000.0, "0.75%")
        elif score >= 650:
            return ("BBB", "Lower Medium Investment Grade", 10000.0, "2.10%")
        elif score >= 600:
            return ("BB", "Non-Investment Speculative", 2500.0, "5.40%")
        elif score >= 550:
            return ("B", "Highly Speculative", 500.0, "12.80%")
        elif score >= 450:
            return ("CCC", "Substantial Risk / Vulnerable", 0.0, "28.50%")
        else:
            return ("D", "Default / Insolvent", 0.0, "95.0%")

    def generate_credit_certificate(
        self,
        agent_address: str,
        chain_id: int = 137,
        validity_seconds: int = 3600
    ) -> Dict[str, Any]:
        """
        Signs an on-chain EIP-712 Credit Certificate for smart contracts and DeFi lenders.
        """
        try:
            agent_checksum = eth_utils.to_checksum_address(agent_address)
        except Exception:
            agent_checksum = "0x0000000000000000000000000000000000000000"

        rating = self.compute_credit_score(agent_address)
        score = rating["credit_score"]
        grade = rating["grade"]
        max_credit = int(rating["max_uncollateralized_loan_usdc"])
        now = int(time.time())
        expires_at = now + validity_seconds

        domain_data = {
            "name": "AgentCreditRatingOracle",
            "version": "1.0.0",
            "chainId": chain_id,
            "verifyingContract": "0x0000000000000000000000000000000000000000"
        }

        types = {
            "EIP712Domain": [
                {"name": "name", "type": "string"},
                {"name": "version", "type": "string"},
                {"name": "chainId", "type": "uint256"},
                {"name": "verifyingContract", "type": "address"}
            ],
            "CreditCertificate": [
                {"name": "agentAddress", "type": "address"},
                {"name": "creditScore", "type": "uint16"},
                {"name": "grade", "type": "string"},
                {"name": "maxCreditLimitUsdc", "type": "uint256"},
                {"name": "expiresAt", "type": "uint256"}
            ]
        }

        message_data = {
            "agentAddress": agent_checksum,
            "creditScore": score,
            "grade": grade,
            "maxCreditLimitUsdc": max_credit,
            "expiresAt": expires_at
        }

        structured_data = {
            "types": types,
            "primaryType": "CreditCertificate",
            "domain": domain_data,
            "message": message_data
        }

        signable_msg = encode_typed_data(full_message=structured_data)
        signed = ORACLE_ACCOUNT.sign_message(signable_msg)

        r_hex = "0x" + signed.r.to_bytes(32, byteorder="big").hex()
        s_hex = "0x" + signed.s.to_bytes(32, byteorder="big").hex()
        v = signed.v

        return {
            "status": "success",
            "agent_address": agent_address,
            "credit_score": score,
            "grade": grade,
            "max_uncollateralized_loan_usdc": max_credit,
            "expires_at": expires_at,
            "oracle_signer": ORACLE_ACCOUNT.address,
            "chain_id": chain_id,
            "v": v,
            "r": r_hex,
            "s": s_hex,
            "signature": f"{r_hex}{s_hex[2:]}{v:02x}"
        }

    def calculate_credit_score(self, agent_address: str) -> Dict[str, Any]:
        """
        Computes FICO-style Agent Credit Score between 300 and 1,000 based on DePIN & task history.
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

        telemetry = self.agent_telemetry.get(addr, {})
        is_blacklisted = telemetry.get("is_blacklisted", False)

        completed = rec["completed_tasks"]
        slashed = rec["slashed_tasks"]
        total_tasks = completed + slashed
        volume = rec["total_volume_usdc"]
        days_active = max(1, (int(time.time()) - rec["first_seen"]) // 86400)

        if is_blacklisted:
            score = 300
        else:
            score = 500.0

            if total_tasks > 0:
                success_rate = completed / total_tasks
                score += success_rate * 250.0

            if volume >= 100000.0:
                score += 150.0
            elif volume >= 10000.0:
                score += 100.0
            elif volume >= 1000.0:
                score += 50.0
            elif volume > 0:
                score += 20.0

            if days_active >= 90:
                score += 100.0
            elif days_active >= 30:
                score += 60.0
            elif days_active >= 7:
                score += 30.0

            score -= (slashed * 200.0)
            score = max(300, min(1000, int(score)))

        if score >= 900:
            tier = "AAA (Sovereign)"
            required_collateral_ratio = 0.0
            max_credit_limit_usdc = 100000.0
        elif score >= 800:
            tier = "AA (Institutional)"
            required_collateral_ratio = 0.25
            max_credit_limit_usdc = 50000.0
        elif score >= 700:
            tier = "A (Verified)"
            required_collateral_ratio = 0.50
            max_credit_limit_usdc = 15000.0
        elif score >= 550:
            tier = "BBB (Standard)"
            required_collateral_ratio = 1.00
            max_credit_limit_usdc = 2000.0
        else:
            tier = "Subprime / Blacklisted"
            required_collateral_ratio = 1.50
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
        expires_at = int(time.time()) + 86400 * 7

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

    def calculate_adaptive_collateral(self, agent_address: str, job_amount_usdc: float) -> Dict[str, Any]:
        """
        Calculates exact worker collateral staking requirement based on agent credit tier.
        High-reputation agents get collateral discounts; unverified/low-reputation agents pay higher stakes.
        """
        score_data = self.calculate_credit_score(agent_address)
        ratio = score_data["required_collateral_ratio"]
        required_stake = round(job_amount_usdc * ratio, 4)

        return {
            "agent_address": score_data["agent_address"],
            "agent_name": score_data["agent_name"],
            "credit_score": score_data["credit_score"],
            "tier": score_data["tier"],
            "job_amount_usdc": job_amount_usdc,
            "collateral_ratio": ratio,
            "required_collateral_usdc": required_stake,
            "can_accept_job": score_data["credit_score"] >= 400
        }

    def slash_agent_stake(
        self,
        agent_address: str,
        job_id: int,
        slash_amount_usdc: float,
        violation_reason: str,
        chain_id: int = 137
    ) -> Dict[str, Any]:
        """
        Executes deterministic forfeiture (slashing) of worker stake upon fraud, hallucination, or contract breach.
        Penalizes credit score and emits cryptographic slashing attestation.
        """
        addr = agent_address.lower()
        self.record_activity(agent_address=addr, is_success=False, task_volume_usdc=slash_amount_usdc)

        new_score = self.calculate_credit_score(agent_address)
        timestamp = int(time.time())

        slash_hash = eth_utils.keccak(text=f"SLASH:{job_id}:{addr}:{slash_amount_usdc}:{violation_reason}:{timestamp}").hex()

        return {
            "status": "SLASHED",
            "job_id": job_id,
            "slashed_agent": eth_utils.to_checksum_address(agent_address),
            "slashed_amount_usdc": slash_amount_usdc,
            "violation_reason": violation_reason,
            "new_credit_score": new_score["credit_score"],
            "new_tier": new_score["tier"],
            "slashing_proof_hash": f"0x{slash_hash}",
            "timestamp": timestamp,
            "message": f"Worker collateral {slash_amount_usdc} USDC slashed and forfeited to protocol insurance pool."
        }

    def evaluate_dynamic_stake_requirement(
        self,
        agent_address: str,
        domain: str = "ESCROW",
        brain_anomaly_flag: bool = False
    ) -> Dict[str, Any]:
        """
        Dynamically calculates worker collateral staking ratio based on:
        1. Agent credit rating tier (AAA: 10%, AA: 15%, A: 20%, BBB: 25%, B/C: 30%)
        2. ElizaOS Brain real-time supply shock or satellite deforestation anomaly
        Invariant: If domain anomaly/shock is active, stake requirement escalates to minimum 30.0%.
        """
        score_info = self.calculate_credit_score(agent_address)
        raw_tier = score_info.get("tier", "BBB")

        if "AAA" in raw_tier:
            base_ratio = 0.10
            clean_tier = "AAA"
        elif "AA" in raw_tier:
            base_ratio = 0.15
            clean_tier = "AA"
        elif "A " in raw_tier or raw_tier.startswith("A"):
            base_ratio = 0.20
            clean_tier = "A"
        elif "BBB" in raw_tier:
            base_ratio = 0.25
            clean_tier = "BBB"
        else:
            base_ratio = 0.35
            clean_tier = "Subprime"

        effective_ratio = base_ratio
        anomaly_escalated = False

        if brain_anomaly_flag and effective_ratio < 0.30:
            effective_ratio = 0.30
            anomaly_escalated = True

        return {
            "agent_address": eth_utils.to_checksum_address(agent_address),
            "tier": clean_tier,
            "raw_tier": raw_tier,
            "credit_score": score_info.get("credit_score", 650),
            "base_ratio": base_ratio,
            "effective_collateral_ratio": effective_ratio,
            "brain_anomaly_detected": brain_anomaly_flag,
            "anomaly_escalation_applied": anomaly_escalated,
            "domain": domain.upper(),
            "directive": "Escalate stake to >= 30% under domain anomaly to disincentivize moral hazard." if anomaly_escalated else "Standard credit-rated collateral."
        }


# Singleton instances & aliases
credit_engine = AgentCreditRatingEngine()
agent_credit_engine = credit_engine
AgentCreditEngine = AgentCreditRatingEngine

__all__ = [
    "AgentCreditRatingEngine",
    "AgentCreditEngine",
    "credit_engine",
    "agent_credit_engine"
]
