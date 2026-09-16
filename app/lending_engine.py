"""
Autonomous Agent Lending Engine.
Computes loan quotes, originations, interest calculations, and coordinates
with AgentCreditOracle for uncollateralized lending pools on Polygon.
"""

from typing import Dict, Any, Optional
from app.credit_rating_engine import credit_engine


class AgentLendingEngine:
    """Manages agent credit loan quotes, qualification checks, and repayment incentives."""

    ANNUAL_INTEREST_BPS = 500  # 5.0% APY
    MIN_ORIGINATION_FEE_BPS = 50  # 0.5% Minimum fee

    def __init__(self):
        self.credit_engine = credit_engine

    def get_loan_quote(
        self,
        agent_address: str,
        requested_amount_usdc: float,
        duration_days: int = 30,
        chain_id: int = 137
    ) -> Dict[str, Any]:
        """
        Evaluates whether an agent qualifies for a loan and returns an official quote
        with an EIP-712 CreditCertificate for on-chain submission to AgentLendingPool.sol.
        """
        import math
        try:
            amount = float(requested_amount_usdc)
        except (ValueError, TypeError):
            return {
                "status": "rejected",
                "agent_address": agent_address,
                "is_eligible": False,
                "reason": f"Invalid loan amount: {requested_amount_usdc}"
            }

        if math.isnan(amount) or math.isinf(amount) or amount <= 0:
            return {
                "status": "rejected",
                "agent_address": agent_address,
                "is_eligible": False,
                "reason": f"Requested loan amount must be strictly positive and finite: ${requested_amount_usdc}"
            }

        if duration_days <= 0 or duration_days > 365:
            return {
                "status": "rejected",
                "agent_address": agent_address,
                "is_eligible": False,
                "reason": f"Loan duration must be between 1 and 365 days (got {duration_days})"
            }

        # 1. Fetch current credit assessment
        credit_report = self.credit_engine.compute_credit_score(agent_address)
        max_limit = credit_report["max_uncollateralized_loan_usdc"]
        is_eligible = (amount <= max_limit) and (credit_report["credit_score"] >= 600)

        # 2. Calculate interest & origination fees
        interest_fee = (amount * self.ANNUAL_INTEREST_BPS * duration_days) / (365 * 10000)
        min_fee = (amount * self.MIN_ORIGINATION_FEE_BPS) / 10000
        applied_fee = round(max(interest_fee, min_fee), 4)
        total_due = round(amount + applied_fee, 4)

        # 3. Issue on-chain credit certificate if eligible
        attestation = None
        if is_eligible:
            attestation = self.credit_engine.generate_credit_certificate(agent_address, chain_id=chain_id)

        return {
            "status": "success",
            "agent_address": agent_address,
            "is_eligible": is_eligible,
            "credit_score": credit_report["credit_score"],
            "grade": credit_report["grade"],
            "requested_amount_usdc": requested_amount_usdc,
            "max_credit_limit_usdc": max_limit,
            "duration_days": duration_days,
            "interest_fee_usdc": applied_fee,
            "total_due_usdc": total_due,
            "apr_percentage": 5.0,
            "attestation": attestation,
            "reason": "Approved" if is_eligible else f"Requested ${requested_amount_usdc:.2f} exceeds credit limit ${max_limit:.2f} or score below 600"
        }

    def record_loan_repayment(self, agent_address: str, loan_id: int, amount_repaid: float) -> Dict[str, Any]:
        """Rewards an agent with a credit score boost upon successful on-chain loan repayment."""
        import math
        try:
            repaid = float(amount_repaid)
        except (ValueError, TypeError):
            raise ValueError(f"Invalid repayment amount: {amount_repaid}")

        if math.isnan(repaid) or math.isinf(repaid) or repaid <= 0:
            raise ValueError(f"Repayment amount must be strictly positive and finite: ${amount_repaid}")

        self.credit_engine.record_audit(agent_address, verdict="PASSED", hallucination_detected=False)
        updated_score = self.credit_engine.compute_credit_score(agent_address)
        return {
            "status": "success",
            "agent_address": agent_address,
            "loan_id": loan_id,
            "amount_repaid": amount_repaid,
            "updated_credit_score": updated_score["credit_score"],
            "updated_grade": updated_score["grade"],
            "message": "Loan repayment successfully recorded. On-chain credit reputation boosted!"
        }


lending_engine = AgentLendingEngine()
