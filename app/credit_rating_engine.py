"""
Autonomous Agent Credit Rating Agency Engine ("Moody's & S&P of AI Agents").
Computes institutional-grade credit scores (300 - 850) and grades (AAA - D)
based on safety compliance, factual faithfulness, economic solvency, and on-chain runway.
"""

import time
from typing import Dict, Any, Optional
from app.vault_manager import vault_manager
from app.onchain_signer import onchain_signer, ORACLE_ACCOUNT
from eth_account import Account
from eth_account.messages import encode_typed_data
import eth_utils


class AgentCreditRatingEngine:
    """
    Evaluates autonomous AI agent trustworthiness, solvency, and operational safety.
    Issues cryptographically verifiable EIP-712 Credit Certificates for DeFi lending protocols.
    """

    def __init__(self):
        # In-memory telemetry store for agent audit records
        # agent_address -> {"audits": int, "blocked": int, "hallucinations": int, "created_at": float}
        self.agent_telemetry: Dict[str, Dict[str, Any]] = {}

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
        volume_score = min(50, total_audits * 2)

        # Composite score
        total_score = 300 + safety_score + faithfulness_score + solvency_score + volume_score
        total_score = max(300, min(850, total_score))

        # Determine Credit Grade & Uncollateralized Lending Limit
        grade, description, max_credit_usdc, default_risk = self._evaluate_tier(total_score, blocked_count)

        return {
            "agent_address": agent_address,
            "credit_score": total_score,
            "grade": grade,
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
            "agentAddress": agent_address,
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


credit_engine = AgentCreditRatingEngine()
