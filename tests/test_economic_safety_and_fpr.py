"""
Comprehensive Economic Safety & False Positive Rate (FPR) Verification Suite.
Validates zero tolerance for:
1. Economic Exploits: Negative amounts, NaN/Inf injection, fee deficits, and budget manipulation
2. False Positives: Legitimate Web3 transfers, EVM addresses, educational security queries, and Korean user interactions
"""

import math
import pytest
from pydantic import ValidationError

from sdk.agent_gate_sdk import BoundedAgentWallet
from app.lending_engine import lending_engine
from app.factoring_engine import AgentFactoringEngine
from app.insurance_engine import AgentInsuranceEngine
from app.trade_engine import AgentTradeIntent
from app.security_engine import analyze_payload_security


# =====================================================================
# 1. Economic Safety: Negative, NaN, Inf, and Budget Invariants
# =====================================================================

class TestEconomicSafetyInvariants:
    """Rigorous mathematical boundary and fund-safety checks."""

    @pytest.fixture
    def wallet(self, tmp_path):
        ledger = tmp_path / "econ_wallet.json"
        return BoundedAgentWallet(
            daily_limit_usdc=10.0,
            per_tx_limit_usdc=1.0,
            whitelist=[BoundedAgentWallet.DEFAULT_SHERIFF_GATE],
            ledger_path=str(ledger)
        )

    def test_bounded_wallet_rejects_negative_spend_attempt(self, wallet):
        """Negative spend must not artificially expand daily budget."""
        recipient = BoundedAgentWallet.DEFAULT_SHERIFF_GATE
        allowed, reason = wallet.can_pay(recipient, -50.0)
        assert allowed is False
        assert "strictly positive and finite" in reason

        # Double check that record_spend raises ValueError
        with pytest.raises(ValueError):
            wallet.record_spend(recipient, -50.0)

        # Budget must remain uncompromised at $0.00
        assert wallet.get_daily_spent() == 0.0

    def test_bounded_wallet_rejects_nan_and_inf_injection(self, wallet):
        """NaN or Infinity values must be strictly rejected."""
        recipient = BoundedAgentWallet.DEFAULT_SHERIFF_GATE

        allowed_nan, _ = wallet.can_pay(recipient, float("nan"))
        assert allowed_nan is False

        allowed_inf, _ = wallet.can_pay(recipient, float("inf"))
        assert allowed_inf is False

        allowed_zero, _ = wallet.can_pay(recipient, 0.0)
        assert allowed_zero is False

    def test_lending_engine_rejects_negative_and_zero_loans(self):
        """Uncollateralized lending pool must reject non-positive loan requests."""
        agent = "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"

        # Negative amount
        neg_quote = lending_engine.get_loan_quote(agent, -100.0)
        assert neg_quote["status"] == "rejected"
        assert neg_quote["is_eligible"] is False
        assert "strictly positive" in neg_quote["reason"]

        # Zero amount
        zero_quote = lending_engine.get_loan_quote(agent, 0.0)
        assert zero_quote["status"] == "rejected"
        assert zero_quote["is_eligible"] is False

        # NaN amount
        nan_quote = lending_engine.get_loan_quote(agent, float("nan"))
        assert nan_quote["status"] == "rejected"

        # Invalid duration
        invalid_duration = lending_engine.get_loan_quote(agent, 50.0, duration_days=0)
        assert invalid_duration["status"] == "rejected"

        # Negative repayment must raise ValueError
        with pytest.raises(ValueError):
            lending_engine.record_loan_repayment(agent, loan_id=1, amount_repaid=-50.0)

    def test_factoring_engine_rejects_underwater_and_nonpositive_invoices(self):
        """Factoring pool must reject negative invoices or invoices with advance <= 0."""
        engine = AgentFactoringEngine()
        agent = "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"

        # Negative face value
        neg_res = engine.get_factoring_quote(
            invoice_id=1,
            escrow_job_id=1,
            agent_address=agent,
            face_value_usdc=-100.0
        )
        assert neg_res["status"] == "rejected"
        assert neg_res["is_eligible"] is False

        # Underwater invoice: $0.10 face value < minimum $0.20 protocol fee
        underwater = engine.get_factoring_quote(
            invoice_id=2,
            escrow_job_id=2,
            agent_address=agent,
            face_value_usdc=0.10
        )
        assert underwater["status"] == "rejected"
        assert underwater["is_eligible"] is False
        assert "insufficient to cover discount and protocol fees" in underwater["reason"]

    def test_insurance_engine_rejects_nonpositive_coverage(self):
        """Insurance policy underwriting must reject zero or negative coverage requests."""
        engine = AgentInsuranceEngine()
        agent = "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"
        beneficiary = "0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC"

        # Negative coverage
        neg_policy = engine.get_policy_quote(
            agent_address=agent,
            beneficiary_address=beneficiary,
            coverage_amount_usdc=-500.0
        )
        assert neg_policy["status"] == "rejected"
        assert neg_policy["is_eligible"] is False

        # Zero coverage
        zero_policy = engine.get_policy_quote(
            agent_address=agent,
            beneficiary_address=beneficiary,
            coverage_amount_usdc=0.0
        )
        assert zero_policy["status"] == "rejected"
        assert zero_policy["is_eligible"] is False

    def test_trade_intent_pydantic_positive_bounds(self):
        """Trade intents must strictly enforce minimum trading sizes."""
        agent = "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"

        # Negative trade size
        with pytest.raises(ValidationError):
            AgentTradeIntent(
                agent_address=agent,
                pair="ETH/USDC",
                direction="BUY",
                amount_usdc=-10.0
            )

        # Micro dust below minimum 0.001 USDC
        with pytest.raises(ValidationError):
            AgentTradeIntent(
                agent_address=agent,
                pair="ETH/USDC",
                direction="BUY",
                amount_usdc=0.0001
            )


# =====================================================================
# 2. False Positive Rate (FPR): Legitimate Web3 & User Queries
# =====================================================================

class TestFalsePositiveRatePrecision:
    """Verifies that legitimate user queries and EVM addresses are never falsely blocked."""

    def test_standard_evm_addresses_not_flagged_as_private_keys(self):
        """
        An EVM address is 42 characters (0x + 40 hex).
        A private key is 66 characters (0x + 64 hex).
        Normal Ethereum addresses must NEVER be flagged as leaked private keys.
        """
        address_query = (
            "Please transfer 15 USDC to recipient 0x70997970C51812dc3A010C7d01b50e0d17dc79C8 "
            "from sender 0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC on Polygon."
        )
        result = analyze_payload_security(address_query)
        assert result["verdict"] == "PASSED"
        assert result["is_safe"] is True
        assert "Secret/Private Key Leak Detected" not in result["threats"]

    def test_legitimate_web3_swap_and_trade_commands_allowed(self):
        """Legitimate decentralized finance and trade actions must be allowed."""
        prompts = [
            "Swap 250 USDC for WETH using Uniswap router on Base chain.",
            "Check current lending APY rates on Aave and Compound.",
            "Deposit 100 USDC into the security gate treasury vault.",
            "Can you fetch the balance of token 0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174?"
        ]
        for p in prompts:
            res = analyze_payload_security(p)
            assert res["verdict"] == "PASSED", f"Falsely blocked legitimate prompt: '{p}'"
            assert res["is_safe"] is True

    def test_korean_natural_conversations_and_market_queries(self):
        """Legitimate Korean agent queries must not trigger false positives."""
        korean_queries = [
            "안녕하세요! 오늘 폴리곤 네트워크 가스비와 이더리움 시세를 알려주세요.",
            "에이전트 보안 게이트 플러그인의 설치 방법과 주요 기능을 요약해줘.",
            "이 작업 결과물이 스마트 컨트랙트 배포 명세서와 일치하는지 검토해줘.",
            "지갑 잔액 100 USDC 중에서 10 USDC를 에스크로 컨트랙트에 예치해줘."
        ]
        for q in korean_queries:
            res = analyze_payload_security(q)
            assert res["verdict"] == "PASSED", f"Falsely blocked Korean query: '{q}'"
            assert res["is_safe"] is True

    def test_educational_and_security_discussion_queries(self):
        """Discussing security concepts objectively must not trigger blocks."""
        educational_queries = [
            "What is prompt injection and how do modern security gates defend against it?",
            "Can you explain the historical origins of the DAN mode jailbreak in LLM research?",
            "Explain how the OWASP Top 10 for LLMs categorizes insecure output handling."
        ]
        for eq in educational_queries:
            res = analyze_payload_security(eq)
            # Should not be blocked (verdict may be PASSED or FLAGGED if containing keyword, but never BLOCKED)
            assert res["verdict"] != "BLOCKED", f"Falsely blocked educational query: '{eq}'"
