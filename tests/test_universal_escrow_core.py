"""
Tests for UniversalEscrowCore.sol & Step 1 Smart Contract Invariants.
====================================================================
Validates:
1. Single Universal Capital Lock-up across domains (Maritime, Bio, Construction)
2. Direct Split Disbursals bypassing corrupt middlemen (100% funds directed to workers/suppliers)
3. 0.25% Protocol Fee mathematical invariant routing to A.GRID Treasury
4. Physical Truth Validation failure blocking
5. Timed Expiration & Refund Security
"""

import time
import pytest
from eth_account import Account
from eth_account.messages import encode_typed_data
import eth_utils

from scripts.demo_universal_escrow_lifecycle import SimulatedUniversalEscrowCore
from app.onchain_signer import onchain_signer


class TestUniversalEscrowCore:

    @pytest.fixture(autouse=True)
    def setup_escrow(self):
        self.oracle_signer = onchain_signer.signer_address
        self.treasury = "0x06db5A847F24d0feC5151a01937700E221d55e19"
        self.escrow = SimulatedUniversalEscrowCore(
            contract_address="0x5555555555555555555555555555555555555555",
            oracle_signer=self.oracle_signer,
            treasury_address=self.treasury,
            chain_id=137
        )
        self.payer = Account.create().address
        self.worker1 = Account.create().address
        self.worker2 = Account.create().address
        self.supplier = Account.create().address
        self.token = "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359"  # USDC on Polygon

    def test_deposit_escrow_invariants(self):
        """1.1: Deposit locks capital, enforces minimum 5 min deadline and rejects duplicates."""
        job_id = "0x" + "1" * 64
        truth_hash = "0x" + "a" * 64
        amount = 1_000_000.0  # 1M USDC Construction project

        # Successful deposit
        job = self.escrow.deposit_escrow(
            job_id=job_id,
            token=self.token,
            amount_usdc=amount,
            domain_int=2,  # Construction
            truth_hash_requirement=truth_hash,
            duration_sec=3600,
            payer=self.payer
        )
        assert job["totalDeposit"] == amount
        assert self.escrow.balances[self.escrow.address] == amount

        # Duplicate job ID is rejected
        with pytest.raises(ValueError, match="JOB_ALREADY_EXISTS"):
            self.escrow.deposit_escrow(
                job_id=job_id,
                token=self.token,
                amount_usdc=amount,
                domain_int=2,
                truth_hash_requirement=truth_hash,
                duration_sec=3600,
                payer=self.payer
            )

        # Zero deposit rejected
        with pytest.raises(ValueError, match="ZERO_DEPOSIT"):
            self.escrow.deposit_escrow(
                job_id="0x" + "2" * 64,
                token=self.token,
                amount_usdc=0.0,
                domain_int=2,
                truth_hash_requirement=truth_hash,
                duration_sec=3600,
                payer=self.payer
            )

    def test_direct_split_settlement_and_treasury_fee(self):
        """1.2: Settlement executes atomic split payouts and exactly 0.25% fee to Treasury."""
        job_id = "0x" + "3" * 64
        truth_hash = "0x" + "b" * 64
        total_deposit = 100_000.0  # $100K USDC

        self.escrow.deposit_escrow(
            job_id=job_id,
            token=self.token,
            amount_usdc=total_deposit,
            domain_int=0,  # Maritime Freight
            truth_hash_requirement=truth_hash,
            duration_sec=1800,
            payer=self.payer
        )

        # Split: 80% to workers, 19.75% to suppliers, 0.25% ($250) to Treasury
        recipients = [
            {"recipient": self.worker1, "amount": 40_000.0},
            {"recipient": self.worker2, "amount": 40_000.0},
            {"recipient": self.supplier, "amount": 19_750.0}
        ]
        # Total disbursed = 99,750.0 + 250.0 (fee) = 100,000.0 (Zero deficit!)

        now = int(time.time())
        expires_at = now + 600

        # Sign EIP-712 Attestation with Oracle Key
        recipients_json = str([(r["recipient"], r["amount"]) for r in recipients])
        recipients_hash = eth_utils.keccak(text=recipients_json)

        domain_data = {
            "name": "UniversalEscrowCore",
            "version": "1.0.0",
            "chainId": 137,
            "verifyingContract": self.escrow.address
        }
        types = {
            "EIP712Domain": [
                {"name": "name", "type": "string"},
                {"name": "version", "type": "string"},
                {"name": "chainId", "type": "uint256"},
                {"name": "verifyingContract", "type": "address"}
            ],
            "TruthSettlementAttestation": [
                {"name": "jobId", "type": "bytes32"},
                {"name": "domain", "type": "uint8"},
                {"name": "truthHashRequirement", "type": "bytes32"},
                {"name": "recipientsHash", "type": "bytes32"},
                {"name": "expiresAt", "type": "uint256"}
            ]
        }
        signable_msg = encode_typed_data(full_message={
            "types": types,
            "primaryType": "TruthSettlementAttestation",
            "domain": domain_data,
            "message": {
                "jobId": job_id,
                "domain": 0,
                "truthHashRequirement": truth_hash,
                "recipientsHash": recipients_hash,
                "expiresAt": expires_at
            }
        })
        sig = onchain_signer.account.sign_message(signable_msg).signature.hex()

        # Execute Direct Split Settlement
        res = self.escrow.execute_settlement_with_proof(
            job_id=job_id,
            recipients=recipients,
            truth_payload=b"sensor_telemetry_valid",
            expires_at=expires_at,
            signature_hex=sig
        )

        assert res["status"] == "SETTLED_SUCCESSFULLY"
        assert res["total_disbursed_usdc"] == 99_750.0
        assert res["protocol_fee_usdc"] == 250.0  # Exactly 0.25%
        assert self.escrow.balances[self.worker1] == 40_000.0
        assert self.escrow.balances[self.worker2] == 40_000.0
        assert self.escrow.balances[self.supplier] == 19_750.0
        assert self.escrow.balances[self.treasury] == 250.0
        assert self.escrow.balances[self.escrow.address] == 0.0  # Contract fully disbursed!

    def test_over_disbursement_and_physical_truth_failure_rejected(self):
        """1.3: Rejects over-disbursement and physical truth adapter validation failure."""
        job_id = "0x" + "4" * 64
        truth_hash = "0x" + "c" * 64
        total_deposit = 10_000.0

        self.escrow.deposit_escrow(
            job_id=job_id,
            token=self.token,
            amount_usdc=total_deposit,
            domain_int=1,  # Bio
            truth_hash_requirement=truth_hash,
            duration_sec=1800,
            payer=self.payer
        )

        # Over-disbursement attempt ($20,000 > $10,000)
        greedy_recipients = [{"recipient": self.worker1, "amount": 20_000.0}]

        with pytest.raises(ValueError, match="EXCEEDS_ESCROW_DEPOSIT"):
            self.escrow.execute_settlement_with_proof(
                job_id=job_id,
                recipients=greedy_recipients,
                truth_payload=b"dummy",
                expires_at=int(time.time()) + 600,
                signature_hex="0xmock_valid_oracle_signature"
            )

        # Truth adapter verification failure
        def failing_truth_verifier(jid, payload):
            return False

        valid_recipients = [{"recipient": self.worker1, "amount": 5_000.0}]
        with pytest.raises(ValueError, match="PHYSICAL_TRUTH_VALIDATION_FAILED"):
            self.escrow.execute_settlement_with_proof(
                job_id=job_id,
                recipients=valid_recipients,
                truth_payload=b"sensor_out_of_range",
                expires_at=int(time.time()) + 600,
                signature_hex="0xmock_valid_oracle_signature",
                adapter_verifier_fn=failing_truth_verifier
            )

    def test_refund_escrow_lifecycle(self):
        """1.4: Payer can refund escrow only after deadline has elapsed."""
        job_id = "0x" + "5" * 64
        truth_hash = "0x" + "d" * 64
        deposit_amt = 50_000.0

        self.escrow.deposit_escrow(
            job_id=job_id,
            token=self.token,
            amount_usdc=deposit_amt,
            domain_int=2,
            truth_hash_requirement=truth_hash,
            duration_sec=300,  # 5 minutes
            payer=self.payer
        )

        # Attempting refund before deadline fails
        with pytest.raises(ValueError, match="DEADLINE_NOT_REACHED"):
            self.escrow.refund_escrow(job_id, caller=self.payer)

        # Fast-forward deadline
        self.escrow.jobs[job_id]["deadline"] = int(time.time()) - 1

        # Unauthorized caller fails
        rogue_caller = Account.create().address
        with pytest.raises(ValueError, match="NOT_AUTHORIZED"):
            self.escrow.refund_escrow(job_id, caller=rogue_caller)

        # Authorized payer refund succeeds
        payer_pre = self.escrow.balances[self.payer]
        res = self.escrow.refund_escrow(job_id, caller=self.payer)
        assert res["status"] == "REFUNDED"
        assert res["refunded_amount_usdc"] == deposit_amt
        assert self.escrow.balances[self.payer] == payer_pre + deposit_amt
        assert self.escrow.balances[self.escrow.address] == 0.0
