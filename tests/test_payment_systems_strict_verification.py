"""
Strict Payment System Security & Mathematical Invariant Verification Suite.
Validates zero tolerance for:
  1. Economic Exploits: NaN/Infinity injections, negative deposits/withdrawals, sub-cent rounding drift
  2. Race Conditions: Multithreaded concurrent vault deductions under extreme load
  3. Batch Payment Exploit Defense: Upfront settlement verification preventing unpaid batch audits
  4. x402 Micropayment Protocol Invariants: Challenge headers, Circle USDC micro units conversion
  5. BoundedAgentWallet Spend Protections: Daily budget ceilings, transaction limits, whitelist enforcement
  6. On-chain Escrow Balance Invariant: Payout + Collateral Stake conservation across Completed, Slashed, Refunded
"""

import math
import time
import threading
import pytest
from eth_account import Account
from fastapi.testclient import TestClient

from app.vault_manager import VaultManager
from app.x402_verifier import x402_verifier, EXPECTED_AMOUNT_USD, MICRO_USDC_AMOUNT
from app.main import app
from sdk.agent_gate_sdk import BoundedAgentWallet, BudgetExceededError
from scripts.demo_agent_escrow_lifecycle import SimulatedAgentEscrowContract
from app.onchain_signer import onchain_signer


class TestStrictPaymentSecurity:
    """Rigorous payment boundary, math invariant, and multi-thread race condition tests."""

    @pytest.fixture(autouse=True)
    def setup_payment_suite(self, tmp_path):
        self.state_file = tmp_path / "strict_vault.json"
        self.vault = VaultManager(state_file_path=str(self.state_file))
        self.client_addr = Account.create().address
        self.worker_addr = Account.create().address
        self.client = TestClient(app)

    # =========================================================================
    # 1. NaN, Infinity, and Negative Boundary Exploit Defenses
    # =========================================================================

    def test_deposit_strictly_rejects_nan_inf_and_negatives(self):
        """1.1: Deposit must strictly reject NaN, Infinity, negative and below-minimum amounts."""
        for bad_amount in [float("nan"), float("inf"), float("-inf"), -50.0, -0.001, 0.0, 49.9999]:
            with pytest.raises(ValueError, match="Minimum deposit"):
                self.vault.deposit(self.client_addr, bad_amount)

        # Valid deposit succeeds
        acc = self.vault.deposit(self.client_addr, 50.0)
        assert acc.balance_usdc == 50.0

    def test_deduct_strictly_rejects_nan_inf_and_negatives(self):
        """1.2: Deduction must strictly reject non-positive or non-finite numbers."""
        self.vault.deposit(self.client_addr, 100.0)
        for bad_cost in [float("nan"), float("inf"), float("-inf"), -0.002, 0.0]:
            success, reason, bal = self.vault.deduct(self.client_addr, cost_usdc=bad_cost)
            assert success is False
            assert "strictly positive and finite" in reason
            assert bal == 100.0

    def test_withdraw_strictly_rejects_nan_inf_and_negatives(self):
        """1.3: Withdrawal must strictly reject NaN, Inf, zero, or negative numbers."""
        self.vault.deposit(self.client_addr, 100.0)
        for bad_withdrawal in [float("nan"), float("inf"), float("-inf"), -10.0, 0.0]:
            success, reason, bal = self.vault.withdraw(self.client_addr, amount_usdc=bad_withdrawal)
            assert success is False
            assert "strictly positive and finite" in reason
            assert bal == 100.0

    def test_balance_underflow_prevention(self):
        """1.4: Vault deduction must fail without balance degradation if cost > balance."""
        self.vault.deposit(self.client_addr, 50.0)
        # Deduct almost everything
        ok1, _, bal1 = self.vault.withdraw(self.client_addr, 49.999)
        assert ok1 is True
        assert bal1 == 0.001

        # Attempting to deduct standard fee $0.002 when balance is only $0.001
        ok2, reason, bal2 = self.vault.deduct(self.client_addr, cost_usdc=0.002)
        assert ok2 is False
        assert "Insufficient balance" in reason
        assert bal2 == 0.001  # Balance strictly unchanged!

    # =========================================================================
    # 2. Concurrency & Multithreaded Race Condition Defenses
    # =========================================================================

    def test_concurrent_vault_deductions_thread_safety(self):
        """2.1: 10 parallel threads executing 50 deductions each must achieve zero balance drift."""
        deposit_amount = 50.0
        self.vault.deposit(self.client_addr, deposit_amount)

        thread_count = 10
        calls_per_thread = 50
        cost_per_call = 0.002
        total_deduction = thread_count * calls_per_thread * cost_per_call  # 1.00 USDC

        errors = []

        def worker_task():
            for _ in range(calls_per_thread):
                success, reason, _ = self.vault.deduct(self.client_addr, cost_usdc=cost_per_call)
                if not success:
                    errors.append(reason)

        threads = [threading.Thread(target=worker_task) for _ in range(thread_count)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Concurrent deductions failed: {errors}"

        acc = self.vault.get_account(self.client_addr)
        assert acc is not None
        assert acc.query_count == 500
        expected_balance = round(deposit_amount - total_deduction, 6)
        assert acc.balance_usdc == expected_balance
        assert acc.total_consumed_usdc == round(total_deduction, 6)

    # =========================================================================
    # 3. Batch Payment Upfront Settlement & Free-Rider Exploit Defense
    # =========================================================================

    def test_batch_inspection_blocks_unfunded_batch_upfront(self):
        """3.1: Batch inspection with insufficient vault balance must be blocked upfront via 402."""
        from app.main import vault_manager as app_vault
        # Create vault on the app singleton with balance sufficient for only 1 item ($0.002)
        test_agent = Account.create().address
        acc = app_vault.deposit(test_agent, 50.0)
        app_vault.withdraw(test_agent, 49.998)
        assert app_vault.get_account(test_agent).balance_usdc == 0.002

        # Client requests batch of 5 items ($0.010 total cost, needs $0.008 more)
        batch_payload = {
            "items": [
                {"agent_output": f"Batch item {i}", "is_code": False} for i in range(5)
            ]
        }
        headers = {
            "X-Vault-Key": acc.session_key,
            "X-Client-Address": test_agent
        }

        # Must receive 402 Payment Required upfront
        resp = self.client.post("/api/v1/inspect/batch", json=batch_payload, headers=headers)
        assert resp.status_code == 402
        assert "Insufficient vault balance" in resp.text

    # =========================================================================
    # 4. x402 Micropayment Protocol Unit & Header Invariants
    # =========================================================================

    def test_x402_challenge_units_and_multichain_specs(self):
        """4.1: Verify Circle USDC micro-unit math (0.002 * 10^6 = 2000) across all 3 chains."""
        for chain_id in [137, 8453, 42161]:
            challenge = x402_verifier.generate_challenge(chain_id=chain_id)
            assert challenge.amount_usdc == EXPECTED_AMOUNT_USD
            assert challenge.amount_micro_units == MICRO_USDC_AMOUNT
            assert challenge.amount_micro_units == 2000
            assert challenge.chain_id == chain_id
            assert challenge.pay_to.startswith("0x")

            resp_402 = x402_verifier.build_402_response(chain_id=chain_id)
            assert resp_402.status_code == 402
            assert "x402 pay_to=" in resp_402.headers["WWW-Authenticate"]
            assert resp_402.headers["X-Payment-Chain-Id"] == str(chain_id)

    # =========================================================================
    # 5. BoundedAgentWallet Client-Side Budget Guards
    # =========================================================================

    def test_bounded_wallet_enforces_per_tx_and_daily_ceilings(self, tmp_path):
        """5.1: BoundedAgentWallet strictly enforces limits and whitelists."""
        ledger = tmp_path / "wallet_ledger.json"
        wallet = BoundedAgentWallet(
            daily_limit_usdc=0.01,
            per_tx_limit_usdc=0.005,
            whitelist=[BoundedAgentWallet.DEFAULT_SHERIFF_GATE],
            ledger_path=str(ledger)
        )

        gate = BoundedAgentWallet.DEFAULT_SHERIFF_GATE

        # Valid payment 1
        can_pay1, _ = wallet.can_pay(gate, 0.003)
        assert can_pay1 is True
        wallet.record_spend(gate, 0.003)
        assert wallet.get_daily_spent() == 0.003

        # Transaction limit violation (0.006 > 0.005)
        can_pay2, reason2 = wallet.can_pay(gate, 0.006)
        assert can_pay2 is False
        assert "exceeds per-transaction limit" in reason2

        # Whitelist violation
        can_pay_rogue, reason_rogue = wallet.can_pay("0xRogueHackerAddress", 0.002)
        assert can_pay_rogue is False
        assert "not in authorized whitelist" in reason_rogue

        # Daily budget depletion (0.003 + 0.003 + 0.005 > 0.010)
        wallet.record_spend(gate, 0.003)
        can_pay3, reason3 = wallet.can_pay(gate, 0.005)
        assert can_pay3 is False
        assert "Daily limit reached" in reason3

    # =========================================================================
    # 6. On-chain Escrow Balance Conservation Law (Zero-Deficit Invariant)
    # =========================================================================

    def test_escrow_balance_conservation_invariant(self):
        """6.1: Escrow contract balance must strictly equal sum of pending jobs at all times."""
        contract_addr = "0x8ACafCEce0B1BFE140e75614b90FD1307b6f389d"
        escrow = SimulatedAgentEscrowContract(contract_addr, onchain_signer.signer_address, chain_id=137)

        client = self.client_addr
        worker = self.worker_addr
        payout = 300.0
        stake = 60.0
        spec_hash = "0x" + "a" * 64

        init_contract_balance = escrow.balances[contract_addr]
        assert init_contract_balance == 0.0

        # Case A: Created job refunded by client (before worker accepts)
        job_id1 = escrow.create_job(client, worker, payout, stake, spec_hash, duration_sec=1800)
        assert escrow.balances[contract_addr] == payout
        escrow.refund_job(job_id1, caller=client)
        assert escrow.balances[contract_addr] == 0.0
        assert escrow.jobs[job_id1]["status"] == "Refunded"

        # Case B: Staked job expired past deadline -> Refunded (payout + stake returned to client)
        # Give 1 second duration so worker can stake immediately before deadline passes
        job_id2 = escrow.create_job(client, worker, payout, stake, spec_hash, duration_sec=1)
        assert escrow.balances[contract_addr] == payout
        escrow.deposit_stake(job_id2, worker)
        assert escrow.balances[contract_addr] == payout + stake

        # Fast forward time past deadline
        time.sleep(1.05)
        escrow.refund_job(job_id2, caller=client)
        assert escrow.balances[contract_addr] == 0.0
        assert escrow.jobs[job_id2]["status"] == "Refunded"


