"""
Unit & Integration Tests for EUDR & Conflict Minerals Truth Adapters and Universal Escrow.
==========================================================================================
Verifies deterministic truth verification, EIP-712 cryptographic proofs, and escrow settlement
for EU Deforestation Regulation (EUDR) and OECD/SEC Responsible Minerals.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.truth_adapters.eudr_truth_adapter import eudr_truth_adapter
from app.truth_adapters.minerals_truth_adapter import minerals_truth_adapter
from sdk.agent_gate_sdk import IndustryDomain

client = TestClient(app)


# --- 1. EudrTruthAdapter Unit Tests ---

def test_eudr_truth_adapter_valid():
    """Test valid EUDR commodity plot verification."""
    result = eudr_truth_adapter.verify_eudr_truth(
        job_id="job_eudr_timber_001",
        commodity="timber",
        country_code="BR",
        polygon_coordinates=[(-3.1234, -60.0123), (-3.1230, -60.0100), (-3.1250, -60.0110)],
        dds_reference_id="EU-DDS-2026-BR-88391",
        deforestation_detected=False,
        legal_harvest_verified=True
    )
    assert result["domain"] == "EUDR_FOREST"
    assert result["domain_id"] == 3
    assert result["is_valid"] is True
    assert result["deforestation_free"] is True
    assert result["legal_harvest_verified"] is True
    assert "signature" in result
    assert result["signature"]["full_signature"].startswith("0x") or len(result["signature"]["full_signature"]) == 130
    assert result["rule_breakdown"]["zero_deforestation_passed"] is True
    assert result["rule_breakdown"]["national_legality_satisfied"] is True


def test_eudr_truth_adapter_deforestation_detected_fails():
    """Security Invariant: Any detected deforestation after 2020-12-31 cutoff must be rejected."""
    result = eudr_truth_adapter.verify_eudr_truth(
        job_id="job_eudr_illegal_clearance",
        commodity="soy",
        country_code="BR",
        polygon_coordinates=[(-12.55, -55.88), (-12.55, -55.80), (-12.60, -55.85)],
        dds_reference_id="EU-DDS-2026-BR-00192",
        deforestation_detected=True,  # Deforestation detected!
        legal_harvest_verified=True
    )
    assert result["is_valid"] is False
    assert result["deforestation_free"] is False
    assert result["rule_breakdown"]["zero_deforestation_passed"] is False


def test_eudr_truth_adapter_invalid_polygon_fails():
    """Geometry Invariant: Plots with fewer than 3 coordinates cannot form a valid closed polygon."""
    result = eudr_truth_adapter.verify_eudr_truth(
        job_id="job_eudr_bad_poly",
        commodity="coffee",
        country_code="VN",
        polygon_coordinates=[(11.94, 108.43), (11.95, 108.44)],  # Only 2 points
        dds_reference_id="EU-DDS-2026-VN-11928",
        deforestation_detected=False,
        legal_harvest_verified=True
    )
    assert result["is_valid"] is False
    assert result["rule_breakdown"]["polygon_integrity"] is False


def test_eudr_truth_adapter_unsupported_commodity_fails():
    """Scope Invariant: Non-EUDR commodities must not be approved."""
    result = eudr_truth_adapter.verify_eudr_truth(
        job_id="job_eudr_bad_commodity",
        commodity="uranium",  # Not an EUDR commodity
        country_code="CA",
        polygon_coordinates=[(55.0, -105.0), (55.1, -105.0), (55.0, -105.1)],
        dds_reference_id="EU-DDS-2026-CA-777",
        deforestation_detected=False,
        legal_harvest_verified=True
    )
    assert result["is_valid"] is False
    assert result["rule_breakdown"]["commodity_supported"] is False


# --- 2. MineralsTruthAdapter Unit Tests ---

def test_minerals_truth_adapter_valid():
    """Test valid conflict-free mineral provenance verification."""
    result = minerals_truth_adapter.verify_minerals_truth(
        job_id="job_minerals_cobalt_001",
        mineral_type="cobalt",
        smelter_id="CID002891",
        smelter_audit_status="CONFORMANT",
        mine_country_code="CD",
        chain_of_custody_verified=True,
        child_labor_free=True,
        conflict_region=True,
        enhanced_due_diligence=True
    )
    assert result["domain"] == "CONFLICT_MINERALS"
    assert result["domain_id"] == 4
    assert result["is_valid"] is True
    assert result["child_labor_free"] is True
    assert result["rule_breakdown"]["smelter_audited"] is True
    assert result["rule_breakdown"]["human_rights_zero_tolerance_passed"] is True
    assert result["rule_breakdown"]["cahra_due_diligence_satisfied"] is True
    assert "signature" in result


def test_minerals_truth_adapter_child_labor_violation_fails():
    """Human Rights Invariant: Child labor violation must result in immediate failure and slashing."""
    result = minerals_truth_adapter.verify_minerals_truth(
        job_id="job_minerals_child_labor_exploit",
        mineral_type="tantalum",
        smelter_id="CID003102",
        smelter_audit_status="CONFORMANT",
        mine_country_code="RW",
        chain_of_custody_verified=True,
        child_labor_free=False,  # Human rights violation!
        conflict_region=False
    )
    assert result["is_valid"] is False
    assert result["rule_breakdown"]["human_rights_zero_tolerance_passed"] is False


def test_minerals_truth_adapter_unconformant_smelter_fails():
    """Smelter Invariant: Un-audited or non-conformant smelters must be rejected."""
    result = minerals_truth_adapter.verify_minerals_truth(
        job_id="job_minerals_bad_smelter",
        mineral_type="gold",
        smelter_id="CID999999",
        smelter_audit_status="SUSPENDED",  # Suspended / non-conformant
        mine_country_code="PE",
        chain_of_custody_verified=True,
        child_labor_free=True
    )
    assert result["is_valid"] is False
    assert result["rule_breakdown"]["smelter_audited"] is False


# --- 3. FastAPI Endpoint Integration Tests ---

def test_api_verify_eudr_endpoint():
    """Integration Test: POST /api/v1/truth/eudr"""
    payload = {
        "job_id": "job_api_eudr_coffee_202",
        "commodity": "coffee",
        "country_code": "ET",
        "polygon_coordinates": [[7.01, 38.50], [7.02, 38.51], [7.01, 38.52]],
        "dds_reference_id": "EU-DDS-2026-ET-44912",
        "deforestation_detected": False,
        "legal_harvest_verified": True
    }
    resp = client.post("/api/v1/truth/eudr", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["domain"] == "EUDR_FOREST"
    assert data["is_valid"] is True
    assert data["deforestation_free"] is True
    assert "signature" in data


def test_api_verify_minerals_endpoint():
    """Integration Test: POST /api/v1/truth/minerals"""
    payload = {
        "job_id": "job_api_minerals_lithium_303",
        "mineral_type": "lithium",
        "smelter_id=":"CID004128",
        "smelter_id": "CID004128",
        "smelter_audit_status": "CONFORMANT",
        "mine_country_code": "CL",
        "chain_of_custody_verified": True,
        "child_labor_free": True,
        "conflict_region": False
    }
    resp = client.post("/api/v1/truth/minerals", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["domain"] == "CONFLICT_MINERALS"
    assert data["is_valid"] is True
    assert "signature" in data


# --- 4. Universal Escrow Direct Split Settlement with EUDR & Minerals Domains ---

def test_universal_escrow_settle_eudr_domain():
    """Escrow Settlement: Settles EUDR plot escrow disbursement (Domain 3)."""
    # 1. Obtain verified attestation
    attestation = eudr_truth_adapter.verify_eudr_truth(
        job_id="job_escrow_eudr_rubber_701",
        commodity="rubber",
        country_code="ID",
        polygon_coordinates=[(-0.55, 101.40), (-0.54, 101.41), (-0.55, 101.42)],
        dds_reference_id="EU-DDS-2026-ID-99211",
        deforestation_detected=False,
        legal_harvest_verified=True
    )

    # 2. Submit to Universal Escrow Settle endpoint
    settle_payload = {
        "job_id": "job_escrow_eudr_rubber_701",
        "domain": 3,  # EUDR_FOREST
        "recipients": [
            {"recipient": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8", "amount": 25000.0}
        ],
        "truth_payload": "EUDR Deforestation-Free Rubber Plot Verified via Sentinel-2",
        "attestation": attestation,
        "chain_id": 137,
        "verifying_contract": "0x5555555555555555555555555555555555555555"
    }
    resp = client.post("/api/v1/escrow/universal/settle", json=settle_payload)
    assert resp.status_code == 200
    res = resp.json()
    assert res["status"] in ("SETTLED", "DISBURSED", "SUCCESS")
    assert res["total_disbursed_usdc"] == 25000.0


def test_universal_escrow_settle_minerals_domain():
    """Escrow Settlement: Settles conflict-free minerals escrow disbursement (Domain 4)."""
    # 1. Obtain verified attestation
    attestation = minerals_truth_adapter.verify_minerals_truth(
        job_id="job_escrow_minerals_tin_801",
        mineral_type="tin",
        smelter_id="CID001928",
        smelter_audit_status="CONFORMANT",
        mine_country_code="MY",
        chain_of_custody_verified=True,
        child_labor_free=True
    )

    # 2. Submit to Universal Escrow Settle endpoint
    settle_payload = {
        "job_id": "job_escrow_minerals_tin_801",
        "domain": 4,  # CONFLICT_MINERALS
        "recipients": [
            {"recipient": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8", "amount": 40000.0}
        ],
        "truth_payload": "RMI Certified Conflict-Free Tin Shipment Tracked",
        "attestation": attestation,
        "chain_id": 137,
        "verifying_contract": "0x5555555555555555555555555555555555555555"
    }
    resp = client.post("/api/v1/escrow/universal/settle", json=settle_payload)
    assert resp.status_code == 200
    res = resp.json()
    assert res["status"] in ("SETTLED", "DISBURSED", "SUCCESS")
    assert res["total_disbursed_usdc"] == 40000.0


def test_universal_escrow_domain_enum_alignment():
    """Enum Test: IndustryDomain enum must contain EUDR_FOREST (3) and CONFLICT_MINERALS (4)."""
    assert IndustryDomain.EUDR_FOREST == 3
    assert IndustryDomain.CONFLICT_MINERALS == 4


def test_universal_escrow_settle_eudr_deforestation_rejected():
    """Security Invariant: Deforestation-detected attestation MUST be rejected at escrow settlement."""
    inv_attestation = eudr_truth_adapter.verify_eudr_truth(
        job_id="job_escrow_eudr_deforest_illegal",
        commodity="timber",
        country_code="BR",
        polygon_coordinates=[(-3.12, -60.02), (-3.12, -60.01), (-3.13, -60.01)],
        dds_reference_id="EU-DDS-2026-BR-ILLEGAL",
        deforestation_detected=True,  # Deforestation!
        legal_harvest_verified=True
    )
    assert inv_attestation["is_valid"] is False
    assert inv_attestation["verdict"] == "FAILED"

    resp = client.post("/api/v1/escrow/universal/settle", json={
        "job_id": "job_escrow_eudr_deforest_illegal",
        "domain": 3,
        "recipients": [{"recipient": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8", "amount": 10000.0}],
        "truth_payload": "Deforested Timber",
        "attestation": inv_attestation
    })
    assert resp.status_code == 400
    assert "Cannot settle escrow" in resp.json()["detail"]


def test_universal_escrow_settle_minerals_child_labor_rejected():
    """Security Invariant: Child labor violation attestation MUST be rejected at escrow settlement."""
    inv_attestation = minerals_truth_adapter.verify_minerals_truth(
        job_id="job_escrow_minerals_child_labor",
        mineral_type="cobalt",
        smelter_id="CID002891",
        smelter_audit_status="CONFORMANT",
        mine_country_code="CD",
        chain_of_custody_verified=True,
        child_labor_free=False  # Human rights violation!
    )
    assert inv_attestation["is_valid"] is False
    assert inv_attestation["verdict"] == "FAILED"

    resp = client.post("/api/v1/escrow/universal/settle", json={
        "job_id": "job_escrow_minerals_child_labor",
        "domain": 4,
        "recipients": [{"recipient": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8", "amount": 20000.0}],
        "truth_payload": "Violating Cobalt",
        "attestation": inv_attestation
    })
    assert resp.status_code == 400
    assert "Cannot settle escrow" in resp.json()["detail"]


def test_universal_escrow_settle_attestation_expired_rejected():
    """Security Invariant: Expired attestation MUST be rejected at escrow settlement."""
    attestation = eudr_truth_adapter.verify_eudr_truth(
        job_id="job_escrow_eudr_expired",
        commodity="coffee",
        country_code="CO",
        polygon_coordinates=[(4.57, -74.29), (4.58, -74.30), (4.59, -74.28)],
        dds_reference_id="EU-DDS-2026-CO-EXP",
        deforestation_detected=False,
        legal_harvest_verified=True
    )
    attestation["expires_at"] = 1000000000
    attestation["expiresAt"] = 1000000000

    resp = client.post("/api/v1/escrow/universal/settle", json={
        "job_id": "job_escrow_eudr_expired",
        "domain": 3,
        "recipients": [{"recipient": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8", "amount": 5000.0}],
        "truth_payload": "Expired Coffee Attestation",
        "attestation": attestation
    })
    assert resp.status_code == 400
    assert "expired" in resp.json()["detail"]

