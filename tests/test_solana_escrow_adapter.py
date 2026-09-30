"""
Test suite for Solana Mainnet Universal Escrow & Ed25519 Truth Adapter.
Verifies Ed25519 cryptographic attestations, SPL USDC zero-deficit settlement,
Base58 address handling, and multi-domain direct split payouts.
"""

import time
import hashlib
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.solana_signer import SolanaOracleSigner, b58encode, b58decode
from app.solana_escrow_adapter import (
    SolanaUniversalEscrowEngine,
    SOLANA_USDC_MINT
)
from sdk.agent_gate_sdk import UniversalEscrowClient, IndustryDomain


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def solana_engine():
    return SolanaUniversalEscrowEngine()


def test_solana_base58_encoding():
    """Verifies pure Python Base58 encoding and decoding round-trip."""
    raw_bytes = b"autonomous_agent_escrow_audit_test"
    encoded = b58encode(raw_bytes)
    assert isinstance(encoded, str)
    decoded = b58decode(encoded)
    assert decoded == raw_bytes

    # Leading zero byte preservation
    with_zeros = b"\x00\x00\x00\x01\x02\x03"
    assert b58decode(b58encode(with_zeros)) == with_zeros


def test_solana_ed25519_attestation_signing_and_verification():
    """Verifies that SolanaOracleSigner generates valid Ed25519 signatures and detects tampering."""
    signer = SolanaOracleSigner()
    job_id = hashlib.sha256(b"job_solana_test_1").digest()
    domain = 0
    truth_hash = hashlib.sha256(b"maritime_telemetry_valid").digest()
    recipients_hash = hashlib.sha256(b"recipients_data").digest()
    expires_at = int(time.time()) + 3600

    attestation = signer.sign_attestation(
        job_id=job_id,
        domain=domain,
        truth_hash=truth_hash,
        recipients_hash=recipients_hash,
        expires_at=expires_at
    )

    assert attestation["chain"] == "solana-mainnet"
    assert attestation["chain_id"] == 501
    assert "oracle_signer_pubkey" in attestation
    assert "signature_b58" in attestation

    # Valid signature check
    is_valid = SolanaOracleSigner.verify_attestation(
        oracle_pubkey_b58=attestation["oracle_signer_pubkey"],
        signature_b58=attestation["signature_b58"],
        job_id=job_id,
        domain=domain,
        truth_hash=truth_hash,
        recipients_hash=recipients_hash,
        expires_at=expires_at
    )
    assert is_valid is True

    # Tampered truth hash check
    is_tampered = SolanaOracleSigner.verify_attestation(
        oracle_pubkey_b58=attestation["oracle_signer_pubkey"],
        signature_b58=attestation["signature_b58"],
        job_id=job_id,
        domain=domain,
        truth_hash=hashlib.sha256(b"tampered_proof").digest(),
        recipients_hash=recipients_hash,
        expires_at=expires_at
    )
    assert is_tampered is False


def test_solana_escrow_settlement_lifecycle(solana_engine):
    """
    Simulates Scenario 1 (Maritime IoT, $250k) on Solana Mainnet with SPL USDC.
    Payer locks 250,000 USDC units ($250,000.00 = 250,000,000,000 base units @ 6 decimals).
    Direct split disburses to 3 suppliers and pays 0.25% protocol fee to A.GRID Treasury.
    """
    job_id = hashlib.sha256(b"solana_maritime_freight_001").digest()
    payer = b58encode(hashlib.sha256(b"payer_shipping_corp").digest())
    total_deposit = 250_000_000_000  # $250k USDC (6 decimals)
    domain = 0  # Maritime

    truth_payload = b'{"voyage":"PACIFIC_EXPRESS_88","temp_kelvin":271.15,"rfid_cleared":true}'
    truth_hash = hashlib.sha256(truth_payload).digest()

    # 1. Create Job Deposit
    job = solana_engine.create_deposit(
        job_id=job_id,
        payer_b58=payer,
        amount_units=total_deposit,
        domain=domain,
        truth_hash_requirement=truth_hash
    )
    assert job.total_deposit == total_deposit

    # 2. Define 3 SPL USDC Beneficiaries
    crew_wallet = b58encode(hashlib.sha256(b"crew_payroll").digest())
    port_wallet = b58encode(hashlib.sha256(b"port_terminal_fees").digest())
    fuel_wallet = b58encode(hashlib.sha256(b"bunker_fuel_depot").digest())

    recipients = [
        {"recipient_b58": crew_wallet, "amount": 100_000_000_000},  # $100k
        {"recipient_b58": port_wallet, "amount": 80_000_000_000},   # $80k
        {"recipient_b58": fuel_wallet, "amount": 60_000_000_000}    # $60k
    ]
    total_payout = 240_000_000_000

    # Compute recipients hash
    recipients_data = b""
    for r in recipients:
        recipients_data += b58decode(r["recipient_b58"]) + r["amount"].to_bytes(8, "little")
    recipients_hash = hashlib.sha256(recipients_data).digest()

    # 3. Oracle signs attestation
    expires_at = int(time.time()) + 3600
    attestation = solana_engine.signer.sign_attestation(
        job_id=job_id,
        domain=domain,
        truth_hash=truth_hash,
        recipients_hash=recipients_hash,
        expires_at=expires_at
    )

    # 4. Settle Escrow
    result = solana_engine.verify_and_settle(
        job_id=job_id,
        truth_payload=truth_payload,
        recipients=recipients,
        oracle_attestation=attestation
    )

    assert result["success"] is True
    assert result["chain"] == "solana-mainnet"
    assert result["total_disbursed"] == total_payout
    assert result["protocol_fee"] == 600_000_000  # 0.25% of 240k = $600
    assert result["recipients_count"] == 3
    assert job.is_settled is True


def test_solana_escrow_invalid_truth_rejection(solana_engine):
    """Verifies that tampering with sensor payload aborts settlement."""
    job_id = hashlib.sha256(b"solana_reject_test").digest()
    payer = b58encode(hashlib.sha256(b"payer").digest())
    truth_hash = hashlib.sha256(b"expected_truth").digest()

    solana_engine.create_deposit(
        job_id=job_id,
        payer_b58=payer,
        amount_units=100_000_000,
        domain=1,
        truth_hash_requirement=truth_hash
    )

    recip = b58encode(hashlib.sha256(b"recip").digest())
    recipients = [{"recipient_b58": recip, "amount": 90_000_000}]

    attestation = solana_engine.signer.sign_attestation(
        job_id=job_id,
        domain=1,
        truth_hash=truth_hash,
        recipients_hash=hashlib.sha256(b58decode(recip) + (90_000_000).to_bytes(8, "little")).digest(),
        expires_at=int(time.time()) + 3600
    )

    with pytest.raises(ValueError, match="Truth hash mismatch"):
        solana_engine.verify_and_settle(
            job_id=job_id,
            truth_payload=b"falsified_corrupted_truth",
            recipients=recipients,
            oracle_attestation=attestation
        )


def test_solana_api_attestation_and_settle_endpoints(client):
    """Verifies FastAPI endpoints for Solana attestation and settle with Base58 addresses."""
    # 1. Attest endpoint
    job_id_hex = hashlib.sha256(b"api_solana_job").hexdigest()
    truth_hex = hashlib.sha256(b"api_solana_truth").hexdigest()
    recip_hex = hashlib.sha256(b"api_solana_recip").hexdigest()

    attest_payload = {
        "job_id_hex": job_id_hex,
        "domain": 2,
        "truth_hash_hex": truth_hex,
        "recipients_hash_hex": recip_hex,
        "validity_seconds": 1800
    }
    res = client.post("/api/v1/escrow/universal/solana/attest", json=attest_payload)
    assert res.status_code == 200
    attest_data = res.json()
    assert attest_data["chain"] == "solana-mainnet"
    assert attest_data["chain_id"] == 501
    assert "signature_b58" in attest_data

    # 2. Settle endpoint with Base58 Solana recipient addresses
    solana_recip1 = b58encode(hashlib.sha256(b"contractor_surveyor_drone").digest())
    solana_recip2 = b58encode(hashlib.sha256(b"materials_concrete_supplier").digest())

    settle_payload = {
        "job_id": f"0x{job_id_hex}",
        "domain": 2,
        "chain_id": 501,
        "recipients": [
            {"recipient": solana_recip1, "amount": 25000.0},
            {"recipient": solana_recip2, "amount": 15000.0}
        ],
        "truth_payload": "LiDAR_PointCloud_BIM_Match_99.2%",
        "attestation": {
            "verdict": "PASSED",
            "expiresAt": int(time.time()) + 3600
        }
    }
    settle_res = client.post("/api/v1/escrow/universal/settle", json=settle_payload)
    assert settle_res.status_code == 200
    settle_data = settle_res.json()
    assert settle_data["status"] == "SETTLED"
    assert settle_data["chain_id"] == 501
    assert settle_data["total_disbursed_usdc"] == 40000.0
    assert settle_data["protocol_fee_usdc"] == 100.0  # 0.25% of 40k = $100


def test_solana_universal_escrow_sdk(client):
    """Verifies UniversalEscrowClient configured for Solana Mainnet."""
    escrow_client = UniversalEscrowClient(chain_id="solana-mainnet", app=app)
    assert escrow_client.chain_id == 501
    assert escrow_client.is_solana is True
    assert escrow_client.contract_address == "AGRIDEscrowUniversalMainnet111111111111111111"

    job = escrow_client.create_job(
        domain=IndustryDomain.CONSTRUCTION_BUILD,
        amount_usdc=100000.0,
        truth_requirement_hash="0x" + "b" * 64
    )
    assert job.amount_usdc == 100000.0

    drone_b58 = b58encode(hashlib.sha256(b"drone_operator_solana").digest())
    settle_res = escrow_client.settle_with_truth(
        job_id=job.job_id,
        proof_data="LiDAR_PointCloud_Valid",
        recipients=[{"recipient": drone_b58, "amount": 95000.0}]
    )
    assert settle_res["status"] in ("SETTLED", "SETTLED_SUCCESSFULLY")
    assert settle_res["domain"] == 2
