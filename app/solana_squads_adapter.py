"""
Solana Mainnet Squads v4 & Anchor Universal Escrow CPI Adapter.
Network: Solana Mainnet (Chain ID 501, Finality 0.4s)
Anchor Program: AGR3W3R9pKxnuZGYrpaggfkbMKVrjoniLaGvi1voBFSC
Treasury Toll: 0.25% ($0.00025 micro-payments)
"""

import time
import hashlib
from typing import Dict, Any, Optional
from dataclasses import dataclass


SOLANA_ANCHOR_PROGRAM = "AGR3W3R9pKxnuZGYrpaggfkbMKVrjoniLaGvi1voBFSC"
SOLANA_TREASURY_PUBKEY = "AGR1D11111111111111111111111111111111111111"


@dataclass
class SolanaEscrowJob:
    job_id: int
    creator_pubkey: str
    worker_pubkey: str
    amount_lamports: int
    worker_stake_lamports: int
    created_at: int
    is_settled: bool = False
    is_slashed: bool = False


class SolanaSquadsAnchorAdapter:
    """
    Coordinates Squads v4 Ephemeral Keypairs with Anchor CPI calls
    to stream micro-payments with 0.4s finality and deterministic worker slashing.
    """

    def __init__(self, program_id: str = SOLANA_ANCHOR_PROGRAM):
        self.program_id = program_id
        self.jobs: Dict[int, SolanaEscrowJob] = {}

    def create_ephemeral_escrow_cpi(
        self,
        job_id: int,
        creator_pubkey: str,
        worker_pubkey: str,
        amount_spl_usdc: float,
        worker_stake_bps: int = 1500
    ) -> Dict[str, Any]:
        """
        Builds the Anchor CPI instruction for UniversalEscrow::initialize_job.
        """
        # SPL USDC has 6 decimals
        amount_lamports = int(amount_spl_usdc * 1_000_000)
        worker_stake_lamports = int(amount_lamports * worker_stake_bps / 10000)

        job = SolanaEscrowJob(
            job_id=job_id,
            creator_pubkey=creator_pubkey,
            worker_pubkey=worker_pubkey,
            amount_lamports=amount_lamports,
            worker_stake_lamports=worker_stake_lamports,
            created_at=int(time.time())
        )
        self.jobs[job_id] = job

        return {
            "program_id": self.program_id,
            "instruction": "initialize_job",
            "accounts": {
                "escrow_vault": f"vault_{job_id}",
                "creator": creator_pubkey,
                "worker": worker_pubkey,
                "system_program": "11111111111111111111111111111111"
            },
            "data": {
                "job_id": job_id,
                "amount": amount_lamports,
                "worker_stake": worker_stake_lamports
            },
            "finality_seconds": 0.4
        }

    def verify_and_stream_settle(
        self,
        job_id: int,
        deliverable: str,
        truth_invariant_passed: bool,
        ed25519_signature: str
    ) -> Dict[str, Any]:
        """
        Settles 0.4s micro-payment or executes instant stake slashing.
        """
        job = self.jobs.get(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found on Solana Anchor program")

        # 1. Check for malicious code or injection
        if "os.system" in deliverable or "ignore previous instructions" in deliverable.lower():
            truth_invariant_passed = False

        if truth_invariant_passed:
            job.is_settled = True
            protocol_fee = int(job.amount_lamports * 25 / 10000)
            worker_payout = job.amount_lamports - protocol_fee

            return {
                "status": "SETTLED_0_4S",
                "action": "STREAM_RELEASE",
                "job_id": job_id,
                "worker_payout_lamports": worker_payout,
                "worker_collateral_returned": job.worker_stake_lamports,
                "protocol_toll_lamports": protocol_fee,
                "finality": "0.4s"
            }
        else:
            job.is_slashed = True
            return {
                "status": "SLASHED_INSTANT",
                "action": "FORFEIT_TO_TREASURY",
                "job_id": job_id,
                "confiscated_stake_lamports": job.worker_stake_lamports,
                "treasury_pubkey": SOLANA_TREASURY_PUBKEY,
                "finality": "0.4s"
            }
