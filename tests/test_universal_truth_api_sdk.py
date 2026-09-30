"""
E2E Tests for Universal Truth Adapters Oracle Endpoints and UniversalEscrowClient SDK.
Tests Step 3 (Oracle REST API) and Step 4 (Enterprise 3-line SDK) from UNIVERSAL_TRUTH_ADAPTER_BLUEPRINT.md.
"""

import time
import pytest
from fastapi.testclient import TestClient
from app.main import app
from sdk import UniversalEscrowClient, IndustryDomain


client = TestClient(app)


def test_oracle_maritime_iot_endpoint_pass():
    """Tests /api/v1/truth/maritime-iot with valid port arrival & cold-chain specs."""
    payload = {
        "job_id": "job_maritime_api_001",
        "current_gps": [51.9500, 4.1400],
        "destination_port_gps": [51.9510, 4.1420],
        "temperature_timeseries_celsius": [-20.1, -19.8, -20.0, -19.5, -20.2],
        "rfid_tag": "RFID-ROTTERDAM-GATE-01",
        "expected_rfid_tag": "RFID-ROTTERDAM-GATE-01",
        "max_geofence_radius_meters": 500.0,
        "chain_id": 137,
        "verifying_contract": "0x5555555555555555555555555555555555555555"
    }
    resp = client.post("/api/v1/truth/maritime-iot", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["verdict"] == "PASSED"
    assert data["domain"] == "TRADE_MARITIME"
    assert data["is_valid"] is True
    assert data["metrics"]["geofence_passed"] is True
    assert data["metrics"]["cold_chain_passed"] is True
    assert "attestation" in data
    assert data["attestation"]["isValid"] is True
    assert data["attestation"]["oracle_signer"].startswith("0x")


def test_oracle_maritime_iot_endpoint_fail_temp():
    """Tests /api/v1/truth/maritime-iot failure when cold chain temp breached."""
    payload = {
        "job_id": "job_maritime_api_fail_002",
        "current_gps": [51.9500, 4.1400],
        "destination_port_gps": [51.9500, 4.1400],
        "temperature_timeseries_celsius": [-20.0, -14.5, -20.0],  # -14.5 breaches -18.0 limit
        "rfid_tag": "RFID-ROTTERDAM-GATE-01",
        "expected_rfid_tag": "RFID-ROTTERDAM-GATE-01",
        "max_geofence_radius_meters": 500.0
    }
    resp = client.post("/api/v1/truth/maritime-iot", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["verdict"] == "FAILED"
    assert data["is_valid"] is False
    assert data["metrics"]["cold_chain_passed"] is False
    assert data["metrics"]["temp_violations_count"] > 0
    assert data["attestation"]["isValid"] is False


def test_oracle_bio_zk_endpoint_pass():
    """Tests /api/v1/truth/bio-zk with valid Merkle root and nanomolar binding affinity."""
    merkle_root = "0x" + "a" * 64
    payload = {
        "job_id": "job_bio_api_001",
        "genomic_merkle_root": merkle_root,
        "expected_merkle_root": merkle_root,
        "binding_affinity_kd_nm": 3.85,
        "kd_threshold_nm": 10.0,
        "zk_proof_hex": "0x" + "e" * 64,
        "tee_enclave_id": "INTEL_SGX_ENCLAVE_V3"
    }
    resp = client.post("/api/v1/truth/bio-zk", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["verdict"] == "PASSED"
    assert data["domain"] == "BIO_KNOWLEDGE_IP"
    assert data["is_valid"] is True
    assert data["metrics"]["merkle_root_verified"] is True
    assert data["metrics"]["kd_affinity_passed"] is True
    assert data["metrics"]["binding_affinity_kd_nm"] == 3.85


def test_oracle_bio_zk_endpoint_fail_affinity():
    """Tests /api/v1/truth/bio-zk failure when affinity Kd exceeds 10.0 nM."""
    merkle_root = "0x" + "b" * 64
    payload = {
        "job_id": "job_bio_api_fail_002",
        "genomic_merkle_root": merkle_root,
        "expected_merkle_root": merkle_root,
        "binding_affinity_kd_nm": 45.2,  # > 10.0 nM
        "kd_threshold_nm": 10.0
    }
    resp = client.post("/api/v1/truth/bio-zk", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["verdict"] == "FAILED"
    assert data["is_valid"] is False
    assert data["metrics"]["kd_affinity_passed"] is False


def test_oracle_build_drone_endpoint_pass():
    """Tests /api/v1/truth/build-drone with valid LiDAR BIM matching & MPa strength."""
    payload = {
        "job_id": "job_drone_api_001",
        "drone_lidar_volume_m3": 4975.0,
        "bim_target_volume_m3": 5000.0,  # 99.5% ratio >= 98.5%
        "concrete_strength_samples_mpa": [29.5, 31.0, 28.4, 30.2],
        "min_volumetric_ratio": 0.985,
        "min_concrete_strength_mpa": 24.0,
        "bim_spec_hash": "0x" + "c" * 64
    }
    resp = client.post("/api/v1/truth/build-drone", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["verdict"] == "PASSED"
    assert data["domain"] == "CONSTRUCTION_BUILD"
    assert data["is_valid"] is True
    assert data["metrics"]["volumetric_passed"] is True
    assert data["metrics"]["volumetric_match_ratio"] >= 0.985
    assert data["metrics"]["concrete_strength_passed"] is True


def test_universal_escrow_settle_endpoint():
    """Tests /api/v1/escrow/universal/settle direct split payout."""
    recipients = [
        {"recipient": "0xRebarSubcontractorAlpha", "amount": 60000.0},
        {"recipient": "0xReadyMixConcreteSupplierBeta", "amount": 40000.0}
    ]
    payload = {
        "job_id": "JOB-BLD-7788",
        "domain": 2,
        "recipients": recipients,
        "truth_payload": "LiDAR match 98.9%, Concrete 32.5 MPa verified",
        "attestation": {
            "jobId": "JOB-BLD-7788",
            "verdict": "PASSED",
            "oracle_signer": "0x90F8bf6A479f320ead074411a4B0e7944Ea8c9C1",
            "proof_hash": "0x" + "d" * 64,
            "expiresAt": int(time.time()) + 3600
        },
        "chain_id": 137,
        "verifying_contract": "0x5555555555555555555555555555555555555555"
    }
    resp = client.post("/api/v1/escrow/universal/settle", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "SETTLED"
    assert data["total_disbursed_usdc"] == 100000.0
    assert data["protocol_fee_usdc"] == 250.0  # 0.25%
    assert len(data["payouts"]) == 2
    assert data["direct_split_executed"] is True


def test_sdk_universal_escrow_3line_construction():
    """Verifies the 3-line Enterprise SDK flow for Construction Drone LiDAR verification."""
    sdk = UniversalEscrowClient(app=app)

    # 1. Lock funds
    job = sdk.create_job(
        domain=IndustryDomain.CONSTRUCTION_BUILD,
        amount_usdc=250000.0,
        truth_requirement_hash="0x" + "e" * 64,
        job_id="job_neom_slab_pour"
    )
    assert job.job_id == "job_neom_slab_pour"
    assert job.status == "DEPOSITED"

    # 2. Settle with Truth & Direct Disbursal to Subcontractors
    settle_res = sdk.settle_with_truth(
        job_id=job.job_id,
        proof_data={"lidar_match": 0.991, "curing_mpa": 31.0},
        recipients=[
            {"recipient": "0xConcreteSupplierA", "amount": 150000.0},
            {"recipient": "0xPumpTruckCrewB", "amount": 50000.0},
            {"recipient": "0xFormworkCarpentersC", "amount": 50000.0}
        ]
    )

    assert settle_res["status"] == "SETTLED_SUCCESSFULLY"
    assert settle_res["total_disbursed_usdc"] == 250000.0
    assert settle_res["protocol_fee_usdc"] == 625.0  # 0.25% of 250,000
    assert job.status == "SETTLED"


def test_sdk_universal_escrow_maritime_and_bio():
    """Verifies the 3-line Enterprise SDK flow across Maritime and Bio domains."""
    sdk = UniversalEscrowClient(app=app)

    # Maritime trade
    job_maritime = sdk.create_job(
        domain=IndustryDomain.TRADE_MARITIME,
        amount_usdc=100000.0,
        truth_requirement_hash="0x" + "f" * 64
    )
    res_m = sdk.settle_with_truth(
        job_id=job_maritime.job_id,
        proof_data="GPS 51.9510, 4.1420 RFID MATCH TEMP -20C",
        recipients=[{"recipient": "0xShippingCarrier", "amount": 100000.0}]
    )
    assert res_m["status"] == "SETTLED_SUCCESSFULLY"
    assert res_m["protocol_fee_usdc"] == 250.0

    # Bio IP
    job_bio = sdk.create_job(
        domain=IndustryDomain.BIO_KNOWLEDGE_IP,
        amount_usdc=50000.0,
        truth_requirement_hash="0x" + "1" * 64
    )
    res_b = sdk.settle_with_truth(
        job_id=job_bio.job_id,
        proof_data="Kd=3.8nM MerkleRoot Valid",
        recipients=[{"recipient": "0xResearchLabUniversity", "amount": 50000.0}]
    )
    assert res_b["status"] == "SETTLED_SUCCESSFULLY"
    assert res_b["protocol_fee_usdc"] == 125.0
