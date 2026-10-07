"""
Bridge Integration Tests: Minerals & EUDR Truth Adapters with Dynamic Trade Escrow.
Validates end-to-end cryptographic invariant:
1. Valid mineral consignment (Copper / Lithium) -> PASSED attestation & valid truthHash for anchorOracleProof.
2. Uncertified smelter or non-compliant supply chain -> FAILED & zero proof signature.
3. EUDR satellite verified polygon -> PASSED attestation & valid truthHash.
4. Mathematical compatibility with DynamicTradeEscrow.sol interface.
"""

import pytest
import eth_utils
from app.truth_adapters.minerals_truth_adapter import MineralsTruthAdapter
from app.truth_adapters.eudr_truth_adapter import EudrTruthAdapter


@pytest.fixture
def minerals_adapter():
    return MineralsTruthAdapter()


@pytest.fixture
def eudr_adapter():
    return EudrTruthAdapter()


def test_copper_trade_escrow_proof_generation(minerals_adapter):
    """
    Simulates high-value Copper trade deal (LME $14,430/t).
    Verifies that MineralsTruthAdapter produces an EIP-712 attestation and truthHash
    directly anchorable in DynamicTradeEscrow.sol (anchorOracleProof).
    """
    deal_id = "0x" + "a1" * 32
    verifying_contract = "0x8ACafCEce0B1BFE140e75614b90FD1307b6f389d"

    result = minerals_adapter.verify_minerals_truth(
        job_id=deal_id,
        mineral_type="copper",
        smelter_id="SMR-CHL-00921",
        smelter_audit_status="CONFORMANT",
        mine_country_code="CL",
        chain_of_custody_verified=True,
        child_labor_free=True,
        conflict_region=False,
        enhanced_due_diligence=True,
        chain_id=137,
        verifying_contract=verifying_contract
    )

    assert result["verdict"] == "PASSED"
    assert result["is_valid"] is True
    assert result["truth_hash"].startswith("0x")
    assert len(result["truth_hash"]) == 66  # bytes32 hex string

    # Signature verification
    sig = result["signature"]
    assert sig["r"].startswith("0x")
    assert sig["s"].startswith("0x")
    assert sig["v"] in (27, 28)

    # Invariant: truthHash is exactly 32 bytes and fits DynamicTradeEscrow.anchorOracleProof(bytes32, bytes32)
    proof_bytes = bytes.fromhex(result["truth_hash"][2:])
    assert len(proof_bytes) == 32


def test_illicit_minerals_consignment_rejected(minerals_adapter):
    """
    Rejects consignment from non-conformant smelter or with child-labor violation.
    """
    deal_id = "0x" + "b2" * 32
    result = minerals_adapter.verify_minerals_truth(
        job_id=deal_id,
        mineral_type="lithium",
        smelter_id="UNKNOWN-ROGUE-99",
        smelter_audit_status="EXPIRED",
        mine_country_code="CD",
        chain_of_custody_verified=False,
        child_labor_free=False,
        conflict_region=True,
        enhanced_due_diligence=False
    )

    assert result["verdict"] == "FAILED"
    assert result["is_valid"] is False
    assert result["isValid"] is False
    assert result["child_labor_free"] is False
    assert result["rule_breakdown"]["human_rights_zero_tolerance_passed"] is False
    # Even on failure, EIP-712 signature is generated as slashing proof with isValid=False
    assert result["signature"]["r"].startswith("0x")


def test_eudr_polygon_truth_attestation(eudr_adapter):
    """
    Validates EUDR satellite verification with GPS geofence polygon for deforestation-free supply chains.
    """
    deal_id = "0x" + "c3" * 32
    result = eudr_adapter.verify_eudr_truth(
        job_id=deal_id,
        commodity="rubber",
        country_code="ID",
        polygon_coordinates=[
            (-0.1234, 101.4567),
            (-0.1240, 101.4580),
            (-0.1255, 101.4570)
        ],
        dds_reference_id="EU-TRACES-2026-ID-99218",
        deforestation_detected=False,
        legal_harvest_verified=True,
        chain_id=137
    )

    assert result["verdict"] == "PASSED"
    assert result["is_valid"] is True
    assert result["deforestation_free"] is True
    assert result["truth_hash"].startswith("0x")
    assert len(result["truth_hash"]) == 66
    assert result["polygon_coordinates_count"] == 3
    assert result["signature"]["r"].startswith("0x")
