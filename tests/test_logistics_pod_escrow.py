"""
Integration and Unit Tests for Logistics Verification Oracle & LogisticsPoDEscrow.
==================================================================================
Tests:
1. DCSA eBL v3.0 standard verification (SCAC, IMO, ISO 6346 container number, UN/LOCODE)
2. Deterministic environmental telemetry Merkle Root calculation
3. Telemetry SLA breach auditing (over-temperature / under-temperature)
4. EIP-712 ProofOfDelivery signature generation and ECDSA signature recovery
5. Full 4-Step Cross-Oracle Supply Chain Finance Pipeline:
   - Step 1: Minerals pricing/provenance + EUDR Deforestation verification
   - Step 2: Shipment verification (DCSA eBL v3.0)
   - Step 3: Transit environmental telemetry Merkle audit
   - Step 4: Proof-of-Delivery attestation & instant atomic payout vs SLA auto-refund
6. MCP Server stdio JSON-RPC tool discovery and execution
"""

import json
import pytest
from eth_account import Account
from eth_account.messages import encode_typed_data
from web3 import Web3

from logistics_oracle_mcp import (
    LogisticsVerificationEngine,
    LOGISTICS_MCP_TOOLS,
    POD_EIP712_TYPES,
    handle_rpc_request
)
from app.truth_adapters.logistics_truth_adapter import LogisticsTruthAdapter, logistics_truth_adapter
from app.truth_adapters.minerals_truth_adapter import MineralsTruthAdapter
from app.truth_adapters.eudr_truth_adapter import EudrTruthAdapter
import mcp_server


@pytest.fixture
def logistics_engine():
    # Use deterministic key for testing
    test_key = "0x4f3edf983ac636a65a842ce7c78d9aa706d3b113bce9c46f30d7d21715b23b1d"
    return LogisticsVerificationEngine(
        private_key=test_key,
        chain_id=8453,
        verifying_contract="0x8ACafCEce0B1BFE140e75614b90FD1307b6f389d"
    )


def test_dcsa_ebl_verification_valid(logistics_engine):
    """Verifies that a conformant DCSA eBL v3.0 returns verified=True and deterministic hashes."""
    res = logistics_engine.verify_dcsa_ebl(
        bl_number="MEDU12345678",
        carrier_scac="MSCU",
        vessel_imo=9876543,
        container_id="MSKU1234567",
        origin_port="CNSHA",
        dest_port="KRPUS"
    )

    assert res["verified"] is True
    assert res["standard"] == "DCSA-eBL-v3.0"
    assert res["carrierScac"] == "MSCU"
    assert res["blDocumentHash"].startswith("0x")
    assert len(res["blDocumentHash"]) == 66
    assert res["containerIdHash"].startswith("0x")
    assert len(res["containerIdHash"]) == 66
    assert res["vesselImo"] == 9876543
    assert res["route"]["pol"] == "CNSHA"
    assert res["route"]["pod"] == "KRPUS"


def test_dcsa_ebl_verification_invalid_container(logistics_engine):
    """Rejects malformed ISO 6346 container number (not 4 letters + 7 digits)."""
    res = logistics_engine.verify_dcsa_ebl(
        bl_number="MEDU12345678",
        carrier_scac="MSCU",
        vessel_imo=9876543,
        container_id="INVALID_CONT",  # Invalid format
        origin_port="CNSHA",
        dest_port="KRPUS"
    )

    assert res["verified"] is False
    assert res["details"]["iso6346FormatValid"] is False


def test_dcsa_ebl_verification_invalid_imo(logistics_engine):
    """Rejects invalid vessel IMO (must be 7 digits between 1000000 and 9999999)."""
    res = logistics_engine.verify_dcsa_ebl(
        bl_number="MEDU12345678",
        carrier_scac="MSCU",
        vessel_imo=123,  # Invalid IMO
        container_id="MSKU1234567",
        origin_port="CNSHA",
        dest_port="KRPUS"
    )

    assert res["verified"] is False
    assert res["details"]["imoValid"] is False


def test_telemetry_merkle_root_determinism(logistics_engine):
    """Confirms Merkle root calculation is deterministic and changes upon tampering."""
    logs_a = [
        {"temp_c": 19.5, "humidity_pct": 55, "ts": 1710000100},
        {"temp_c": 20.1, "humidity_pct": 54, "ts": 1710000200},
        {"temp_c": 19.8, "humidity_pct": 56, "ts": 1710000300},
    ]

    root_1 = logistics_engine.compute_merkle_root(logs_a)
    root_2 = logistics_engine.compute_merkle_root(logs_a)
    assert root_1 == root_2
    assert root_1.startswith("0x")
    assert len(root_1) == 66

    # Tampered logs
    logs_tampered = [
        {"temp_c": 19.5, "humidity_pct": 55, "ts": 1710000100},
        {"temp_c": 29.9, "humidity_pct": 54, "ts": 1710000200},  # Tampered
        {"temp_c": 19.8, "humidity_pct": 56, "ts": 1710000300},
    ]
    root_tampered = logistics_engine.compute_merkle_root(logs_tampered)
    assert root_tampered != root_1


def test_telemetry_sla_audit(logistics_engine):
    """Tests SLA audit for temperature compliance and threshold breaches."""
    clean_logs = [
        {"temp_c": 18.0, "ts": 1710000100},
        {"temp_c": 22.5, "ts": 1710000200},
        {"temp_c": 24.9, "ts": 1710000300},
    ]
    audit_clean = logistics_engine.audit_telemetry(clean_logs, max_allowed_temp_c=25.0)
    assert audit_clean["conditionPassed"] is True
    assert audit_clean["violationCount"] == 0

    breached_logs = [
        {"temp_c": 18.0, "ts": 1710000100},
        {"temp_c": 27.2, "ts": 1710000200},  # SLA breach > 25.0C
        {"temp_c": 21.0, "ts": 1710000300},
    ]
    audit_breached = logistics_engine.audit_telemetry(breached_logs, max_allowed_temp_c=25.0)
    assert audit_breached["conditionPassed"] is False
    assert audit_breached["violationCount"] == 1
    assert audit_breached["violations"][0]["type"] == "OVER_TEMPERATURE"


def test_eip712_pod_attestation_signature_recovery(logistics_engine):
    """
    Verifies that the issued EIP-712 signature correctly recovers to the oracle's public address.
    """
    deal_id = "0x" + "aa" * 32
    bl_doc_hash = "0x" + "bb" * 32
    container_id = "MSKU1234567"
    vessel_imo = 9876543
    dest_unlocode = "KRPUS"
    sensor_logs = [{"temp_c": 19.2, "ts": 1710000000}]

    attestation = logistics_engine.issue_pod_attestation(
        deal_id_hex=deal_id,
        bl_doc_hash=bl_doc_hash,
        container_id=container_id,
        vessel_imo=vessel_imo,
        dest_unlocode=dest_unlocode,
        sensor_logs=sensor_logs,
        max_allowed_temp_c=25.0
    )

    assert attestation["oracleSigner"] == logistics_engine.signer_address
    assert attestation["escrowAction"] == "READY_FOR_INSTANT_RELEASE"
    assert attestation["podStruct"]["conditionPassed"] is True

    # Reconstruct EIP-712 signable to cryptographically recover signer
    domain = {
        "name": "AGridLogisticsOracle",
        "version": "1",
        "chainId": logistics_engine.chain_id,
        "verifyingContract": logistics_engine.verifying_contract,
    }
    pod = attestation["podStruct"]
    message_data = {
        "dealId": bytes.fromhex(pod["dealId"][2:]),
        "blDocumentHash": bytes.fromhex(pod["blDocumentHash"][2:]),
        "containerIdHash": bytes.fromhex(pod["containerIdHash"][2:]),
        "vesselImo": pod["vesselImo"],
        "unlocodeDestination": bytes.fromhex(pod["unlocodeDestination"][2:]),
        "telemetryMerkleRoot": bytes.fromhex(pod["telemetryMerkleRoot"][2:]),
        "deliveryTimestamp": pod["deliveryTimestamp"],
        "conditionPassed": pod["conditionPassed"],
    }

    signable = encode_typed_data(domain, POD_EIP712_TYPES, message_data)
    recovered_addr = Account.recover_message(signable, signature=attestation["eip712Signature"])
    assert recovered_addr == logistics_engine.signer_address


def test_sla_breach_triggers_dispute_action(logistics_engine):
    """
    When environmental SLA is violated (e.g. cold-chain breakdown),
    attestation conditionPassed is False and escrow action triggers dispute/auto-refund.
    """
    deal_id = "0x" + "cc" * 32
    bl_doc_hash = "0x" + "dd" * 32
    container_id = "MSKU7654321"
    vessel_imo = 9123456
    dest_unlocode = "NLRTM"
    sensor_logs = [
        {"temp_c": 28.5, "ts": 1710000000}  # Over limit (limit: 20.0C)
    ]

    attestation = logistics_engine.issue_pod_attestation(
        deal_id_hex=deal_id,
        bl_doc_hash=bl_doc_hash,
        container_id=container_id,
        vessel_imo=vessel_imo,
        dest_unlocode=dest_unlocode,
        sensor_logs=sensor_logs,
        max_allowed_temp_c=20.0
    )

    assert attestation["podStruct"]["conditionPassed"] is False
    assert attestation["escrowAction"] == "DISPUTE_TRIGGERED_BY_SLA_BREACH"


def test_end_to_end_cross_oracle_supply_chain_pipeline():
    """
    Simulates the entire autonomous B2B cross-oracle pipeline:
    1. Step 1 (Trade Genesis): Minerals Oracle validates Copper lot + EUDR validates non-deforestation polygon.
    2. Step 2 (Shipment): Logistics Oracle validates DCSA eBL v3.0, yielding blDocumentHash.
    3. Step 3 (Transit): Logistics Oracle audits environmental telemetry Merkle root.
    4. Step 4 (Delivery & Settlement): Proof-of-Delivery attestation unlocks escrow payout.
    """
    deal_id = "0x" + "77" * 32
    verifying_contract = "0x8ACafCEce0B1BFE140e75614b90FD1307b6f389d"

    # Step 1: Minerals & EUDR
    minerals_oracle = MineralsTruthAdapter()
    eudr_oracle = EudrTruthAdapter()

    minerals_res = minerals_oracle.verify_minerals_truth(
        job_id=deal_id,
        mineral_type="copper",
        smelter_id="SMR-CHL-00921",
        smelter_audit_status="CONFORMANT",
        mine_country_code="CL",
        chain_of_custody_verified=True,
        child_labor_free=True,
        chain_id=8453,
        verifying_contract=verifying_contract
    )
    assert minerals_res["verdict"] == "PASSED"

    polygon_coords = [
        (-3.12345, 29.87654),
        (-3.12400, 29.87700),
        (-3.12500, 29.87600),
        (-3.12345, 29.87654)
    ]
    eudr_res = eudr_oracle.verify_eudr_truth(
        job_id=deal_id,
        commodity="wood",
        polygon_coordinates=polygon_coords,
        country_code="CD",
        dds_reference_id="DDS-EUDR-2026-9921",
        chain_id=8453,
        verifying_contract=verifying_contract
    )

    assert eudr_res["verdict"] == "PASSED"

    # Step 2: Logistics eBL Verification
    logistics_adapter = LogisticsTruthAdapter()
    ebl_res = logistics_adapter.verify_ebl(
        bl_number="HLCU123456789",
        carrier_scac="HLCU",
        vessel_imo=9765432,
        container_id="HLXU9876543",
        origin_port="CLVAP",   # Valparaiso, Chile
        dest_port="KRPUS"      # Busan, Korea
    )
    assert ebl_res["verified"] is True
    expected_bl_hash = ebl_res["blDocumentHash"]
    expected_container_hash = ebl_res["containerIdHash"]

    # Step 3 & 4: Transit Merkle Audit & Delivery Attestation
    transit_sensor_logs = [
        {"temp_c": 18.2, "humidity_pct": 52, "gps": [35.1028, 129.0403], "ts": 1711000100},
        {"temp_c": 19.0, "humidity_pct": 50, "gps": [35.1030, 129.0405], "ts": 1711000200},
        {"temp_c": 19.5, "humidity_pct": 51, "gps": [35.1029, 129.0404], "ts": 1711000300},
    ]

    pod_attestation = logistics_adapter.issue_pod_attestation(
        deal_id=deal_id,
        bl_document_hash=expected_bl_hash,
        container_id="HLXU9876543",
        vessel_imo=9765432,
        dest_unlocode="KRPUS",
        sensor_logs=transit_sensor_logs,
        max_allowed_temp_c=25.0,
        max_geofence_meters=500.0
    )

    assert pod_attestation["escrowAction"] == "READY_FOR_INSTANT_RELEASE"
    assert pod_attestation["podStruct"]["blDocumentHash"] == expected_bl_hash
    assert pod_attestation["podStruct"]["containerIdHash"] == expected_container_hash
    assert pod_attestation["podStruct"]["conditionPassed"] is True
    assert pod_attestation["geofenceAudit"]["geofencePassed"] is True
    assert pod_attestation["geofenceAudit"]["arrivalDistanceMeters"] < 50.0
    assert pod_attestation["eip712Signature"].startswith("0x")


@pytest.mark.asyncio
async def test_mcp_server_logistics_tool_dispatch():
    """Verifies that the main MCP server (mcp_server.py) lists and executes logistics tools."""
    # 1. Tools list contains logistics tools
    tools_resp = await mcp_server.handle_rpc_request({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/list",
        "params": {}
    })
    tool_names = [t["name"] for t in tools_resp["result"]["tools"]]
    assert "logistics_verify_ebl" in tool_names
    assert "logistics_audit_telemetry" in tool_names
    assert "logistics_issue_pod_attestation" in tool_names

    # 2. Call logistics_verify_ebl tool
    call_resp = await mcp_server.handle_rpc_request({
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "logistics_verify_ebl",
            "arguments": {
                "blNumber": "MAEU998877",
                "carrierScac": "MAEU",
                "vessel_imo": 9555111,
                "vesselImo": 9555111,
                "containerId": "MSKU1122334",
                "originPort": "SGSIN",
                "destPort": "NLRTM"
            }
        }
    })
    content = json.loads(call_resp["result"]["content"][0]["text"])
    assert content["verified"] is True
    assert content["carrierScac"] == "MAEU"
    assert content["blDocumentHash"].startswith("0x")


def test_haversine_distance_calculation():
    """Validates spherical Haversine distance accuracy between known coordinates."""
    from logistics_oracle_mcp import haversine_distance_meters, GLOBAL_PORT_UNLOCODE_COORDINATES

    # Busan Port coordinates
    busan_lat, busan_lon = GLOBAL_PORT_UNLOCODE_COORDINATES["KRPUS"]
    # Same point distance should be 0.0
    assert haversine_distance_meters(busan_lat, busan_lon, busan_lat, busan_lon) == 0.0

    # ~100m offset roughly (0.0009 degrees latitude is ~100 meters)
    offset_lat = busan_lat + 0.0009
    dist = haversine_distance_meters(busan_lat, busan_lon, offset_lat, busan_lon)
    assert 90.0 <= dist <= 110.0


def test_telemetry_geofence_arrival_pass_and_fail(logistics_engine):
    """
    Validates that:
    1. A vessel arriving within 500m of the port destination passes the geofence audit.
    2. A vessel outside the 500m geofence fails the audit with GEOFENCE_NOT_ARRIVED.
    """
    from logistics_oracle_mcp import GLOBAL_PORT_UNLOCODE_COORDINATES
    busan_lat, busan_lon = GLOBAL_PORT_UNLOCODE_COORDINATES["KRPUS"]

    # 1. Arrival inside geofence (~50m from berth)
    inside_logs = [
        {"temp_c": 19.0, "gps": [busan_lat + 0.0003, busan_lon + 0.0002], "ts": 1712000100}
    ]
    res_inside = logistics_engine.audit_telemetry(
        sensor_logs=inside_logs,
        dest_unlocode="KRPUS",
        max_geofence_meters=500.0
    )
    assert res_inside["conditionPassed"] is True
    assert res_inside["geofenceAudit"]["geofencePassed"] is True
    assert res_inside["geofenceAudit"]["arrivalDistanceMeters"] < 100.0

    # 2. Arrival outside geofence (5km away)
    outside_logs = [
        {"temp_c": 19.0, "gps": [busan_lat + 0.05, busan_lon + 0.05], "ts": 1712000100}
    ]
    res_outside = logistics_engine.audit_telemetry(
        sensor_logs=outside_logs,
        dest_unlocode="KRPUS",
        max_geofence_meters=500.0
    )
    assert res_outside["conditionPassed"] is False
    assert res_outside["geofenceAudit"]["geofencePassed"] is False
    assert res_outside["violations"][0]["type"] == "GEOFENCE_NOT_ARRIVED"
    assert res_outside["violations"][0]["observedDistanceMeters"] > 5000.0


def test_telemetry_eseal_tampering_rejection(logistics_engine):
    """
    Validates that if an Electronic Seal (E-Seal) is breached or tampered with in transit,
    the condition is rejected and flags E_SEAL_TAMPERED.
    """
    tampered_logs = [
        {"temp_c": 20.0, "seal_tampered": True, "ts": 1712000100}
    ]
    res = logistics_engine.audit_telemetry(
        sensor_logs=tampered_logs,
        dest_unlocode="NLRTM"
    )
    assert res["conditionPassed"] is False
    assert res["violationCount"] == 1
    assert res["violations"][0]["type"] == "E_SEAL_TAMPERED"


def test_geofence_arrival_in_pod_attestation(logistics_engine):
    """
    End-to-end check that issue_pod_attestation includes geofenceAudit
    and verifies arrival within 500m of Rotterdam (NLRTM).
    """
    from logistics_oracle_mcp import GLOBAL_PORT_UNLOCODE_COORDINATES
    rtm_lat, rtm_lon = GLOBAL_PORT_UNLOCODE_COORDINATES["NLRTM"]

    deal_id = "0x" + "88" * 32
    bl_doc_hash = "0x" + "99" * 32
    container_id = "MSKU9988776"
    vessel_imo = 9432109

    # Valid arrival at Rotterdam terminal (< 200m)
    logs = [
        {"temp_c": 18.5, "gps": [rtm_lat + 0.001, rtm_lon + 0.001], "ts": 1712000200}
    ]

    attestation = logistics_engine.issue_pod_attestation(
        deal_id_hex=deal_id,
        bl_doc_hash=bl_doc_hash,
        container_id=container_id,
        vessel_imo=vessel_imo,
        dest_unlocode="NLRTM",
        sensor_logs=logs,
        max_geofence_meters=500.0
    )

    assert attestation["escrowAction"] == "READY_FOR_INSTANT_RELEASE"
    assert attestation["podStruct"]["conditionPassed"] is True
    assert "geofenceAudit" in attestation
    assert attestation["geofenceAudit"]["geofencePassed"] is True
    assert attestation["geofenceAudit"]["destPort"] == "NLRTM"

