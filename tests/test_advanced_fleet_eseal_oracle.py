"""Integration Tests for Advanced Fleet & Electronic Seal (E-Seal) PoD Oracle.

Verifies:
1. Mathematical precision of Mean Kinetic Temperature (MKT) per USP/WHO pharmaceutical guidelines.
2. Legitimate autonomous delivery with GNSS geofence arrival, hardware cryptogram, and EIP-712 attestation.
3. Anti-tampering defense & immediate worker collateral slashing on physical seal violation.
4. Cryptographic hardware signature mismatch / replay attack detection.
5. Cumulative time-series cold-chain breach detection and settlement refusal.
"""

import time
import eth_utils
import pytest
from app.autonomous_fleet_pod_oracle import (
    AutonomousFleetPoDOracle,
    calculate_mean_kinetic_temperature,
)
from app.vault_manager import vault_manager, AgentVaultAccount


@pytest.fixture
def oracle():
    """Returns a fresh instance of AutonomousFleetPoDOracle with pre-funded shipper vault."""
    inst = AutonomousFleetPoDOracle()
    # Pre-fund shipper
    shipper = "0x1111111111111111111111111111111111111111"
    clean_shipper = eth_utils.to_checksum_address(shipper)
    account = AgentVaultAccount(
        agent_address=clean_shipper,
        balance_usdc=5000.0,
        total_deposited_usdc=5000.0,
        total_consumed_usdc=0.0,
        session_key="ak_shipper_test",
        created_at_utc="2026-10-29T00:00:00Z",
        last_active_utc="2026-10-29T00:00:00Z",
        query_count=0
    )
    with vault_manager._lock:
        vault_manager._accounts[clean_shipper] = account

    # Pre-fund carrier
    carrier = "0x2222222222222222222222222222222222222222"
    clean_carrier = eth_utils.to_checksum_address(carrier)
    carrier_acc = AgentVaultAccount(
        agent_address=clean_carrier,
        balance_usdc=50.0,  # $50.0 collateral stake
        total_deposited_usdc=50.0,
        total_consumed_usdc=0.0,
        session_key="ak_carrier_test",
        created_at_utc="2026-10-29T00:00:00Z",
        last_active_utc="2026-10-29T00:00:00Z",
        query_count=0
    )
    with vault_manager._lock:
        vault_manager._accounts[clean_carrier] = carrier_acc

    return inst


def test_mkt_calculation_accuracy():
    """Verify Mean Kinetic Temperature calculation on varying cold-chain profile."""
    # Profile: mostly -20C, with occasional mild spike to -15C
    temps = [-20.0, -20.5, -19.8, -15.0, -18.5, -20.0]
    mkt = calculate_mean_kinetic_temperature(temps)
    # MKT gives more weight to higher temperatures due to exponential Arrhenius factor
    assert -20.5 < mkt < -15.0
    assert mkt > sum(temps) / len(temps)  # MKT is mathematically higher than simple arithmetic mean


def test_advanced_pod_legitimate_delivery(oracle):
    """Verify complete valid delivery passes with E-Seal signature and MKT analysis."""
    shipper = "0x1111111111111111111111111111111111111111"
    carrier = "0x2222222222222222222222222222222222222222"
    pubkey_hash = "hw_eseal_pubkey_abc123"

    oracle.register_delivery_mission(
        mission_id="MISSION-EUDR-001",
        shipper_address=shipper,
        carrier_address=carrier,
        cargo_description="Ultra-low Temp Bio-Therapeutics",
        freight_amount_usdc=1000.0,
        target_lat=51.9244,  # Port of Rotterdam
        target_lon=4.4777,
        eseal_pubkey_hash=pubkey_hash,
        geofence_radius_meters=300.0,
        max_temp_celsius=-18.0,
        min_temp_celsius=-25.0
    )

    nonce = "nonce_9999"
    # Hardware E-Seal generates signature over pubkey_hash:nonce:tamper_flag
    sig = eth_utils.keccak(text=f"{pubkey_hash}:{nonce}:False").hex()

    telemetry = [
        {"temp_celsius": -21.0, "duration_seconds": 600},
        {"temp_celsius": -20.5, "duration_seconds": 600},
        {"temp_celsius": -19.5, "duration_seconds": 600},
    ]

    result = oracle.verify_advanced_pod_and_settle(
        mission_id="MISSION-EUDR-001",
        carrier_address=carrier,
        delivery_lat=51.9245,  # within ~20m
        delivery_lon=4.4778,
        eseal_hardware_payload={
            "tamper_detected": False,
            "nonce": nonce,
            "signature_hex": sig
        },
        cold_chain_telemetry_series=telemetry,
        max_allowed_breach_minutes=15
    )

    assert result["status"] == "DELIVERED_AND_SETTLED"
    assert result["gross_freight_usdc"] == 1000.0
    assert result["protocol_fee_usdc"] == 2.50  # 0.25% toll
    assert result["net_payout_usdc"] == 997.50
    assert result["mkt_celsius"] is not None
    assert "0x" in result["attestation"]["signature"]


def test_eseal_tamper_slashing(oracle):
    """Verify that detected physical seal tampering immediately reverts and slashes carrier collateral."""
    shipper = "0x1111111111111111111111111111111111111111"
    carrier = "0x2222222222222222222222222222222222222222"
    pubkey_hash = "hw_eseal_pubkey_tamper_test"

    oracle.register_delivery_mission(
        mission_id="MISSION-TAMPER-002",
        shipper_address=shipper,
        carrier_address=carrier,
        cargo_description="High-Value Microchip Cargo",
        freight_amount_usdc=500.0,
        target_lat=37.7749,
        target_lon=-122.4194,
        eseal_pubkey_hash=pubkey_hash
    )

    carrier_clean = eth_utils.to_checksum_address(carrier)
    initial_carrier_balance = vault_manager.get_account(carrier_clean).balance_usdc

    # Carrier breached physical container seal
    with pytest.raises(ValueError, match="CRITICAL E-SEAL BREACH: Physical seal tamper detected"):
        oracle.verify_advanced_pod_and_settle(
            mission_id="MISSION-TAMPER-002",
            carrier_address=carrier,
            delivery_lat=37.7750,
            delivery_lon=-122.4195,
            eseal_hardware_payload={
                "tamper_detected": True,
                "nonce": "tamper_nonce",
                "signature_hex": "0x123"
            }
        )

    # Carrier balance was slashed
    new_carrier_balance = vault_manager.get_account(carrier_clean).balance_usdc
    assert new_carrier_balance == initial_carrier_balance - 10.0


def test_cryptogram_forgery_defense(oracle):
    """Verify that forged or replayed hardware signatures are rejected."""
    shipper = "0x1111111111111111111111111111111111111111"
    carrier = "0x2222222222222222222222222222222222222222"
    pubkey_hash = "hw_eseal_pubkey_forgery_test"

    oracle.register_delivery_mission(
        mission_id="MISSION-FORGE-003",
        shipper_address=shipper,
        carrier_address=carrier,
        cargo_description="Pharmaceutical Enzymes",
        freight_amount_usdc=300.0,
        target_lat=40.7128,
        target_lon=-74.0060,
        eseal_pubkey_hash=pubkey_hash
    )

    with pytest.raises(ValueError, match="E-Seal hardware cryptogram signature mismatch"):
        oracle.verify_advanced_pod_and_settle(
            mission_id="MISSION-FORGE-003",
            carrier_address=carrier,
            delivery_lat=40.7128,
            delivery_lon=-74.0060,
            eseal_hardware_payload={
                "tamper_detected": False,
                "nonce": "fake_nonce",
                "signature_hex": "0xdeadbeefcafebabe000000000000000000000000"
            }
        )


def test_cold_chain_cumulative_breach_block(oracle):
    """Verify that cumulative temperature breach over allowable limit blocks settlement."""
    shipper = "0x1111111111111111111111111111111111111111"
    carrier = "0x2222222222222222222222222222222222222222"
    pubkey_hash = "hw_eseal_cold_chain_breach"

    oracle.register_delivery_mission(
        mission_id="MISSION-COLD-004",
        shipper_address=shipper,
        carrier_address=carrier,
        cargo_description="Frozen Vaccines",
        freight_amount_usdc=800.0,
        target_lat=35.6762,
        target_lon=139.6503,
        eseal_pubkey_hash=pubkey_hash,
        max_temp_celsius=-18.0
    )

    nonce = "cold_nonce"
    sig = eth_utils.keccak(text=f"{pubkey_hash}:{nonce}:False").hex()

    # 20 minutes breach at -10C (above -18C max), where max allowed is 15 minutes
    breached_telemetry = [
        {"temp_celsius": -10.0, "duration_seconds": 1200},  # 20 minutes breach!
        {"temp_celsius": -20.0, "duration_seconds": 600},
    ]

    with pytest.raises(ValueError, match="Cumulative cold-chain breach 20.0m exceeded maximum allowable 15m"):
        oracle.verify_advanced_pod_and_settle(
            mission_id="MISSION-COLD-004",
            carrier_address=carrier,
            delivery_lat=35.6762,
            delivery_lon=139.6503,
            eseal_hardware_payload={
                "tamper_detected": False,
                "nonce": nonce,
                "signature_hex": sig
            },
            cold_chain_telemetry_series=breached_telemetry,
            max_allowed_breach_minutes=15
        )
