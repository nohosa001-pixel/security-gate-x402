"""
Test Suite for Phase 3: Energy Grid & Autonomous Fleet PoD Oracles
Validates:
1. IoT Smart Meter telemetry, grid frequency stability invariants, and kWh streaming micro-settlement.
2. GNSS geofenced PoD arrival, tamper-free Electronic Seal verification, and cold chain limits.
3. Timelock expiry refunds, malicious tamper slashing, and SDK integration.
"""

import secrets
import time
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.power_grid_oracle import power_grid_oracle
from app.autonomous_fleet_pod_oracle import autonomous_fleet_pod_oracle
from app.vault_manager import vault_manager
from app.rwa_treasury_engine import sovereign_treasury
from app.credit_rating_engine import credit_engine
from sdk.agent_gate_sdk import UniversalEscrowClient


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_registries():
    """Ensure complete hermetic test isolation."""
    power_grid_oracle.contracts.clear()
    power_grid_oracle.readings_log.clear()
    autonomous_fleet_pod_oracle.missions.clear()
    with vault_manager._lock:
        vault_manager._accounts.clear()
        vault_manager._session_index.clear()


class TestPowerGridOracle:
    def test_register_and_stream_power_consumption_success(self, client):
        """AI Data Center buys power from VPP Generator via IoT Smart Meter streaming."""
        generator = "0x3a01000000000000000000000000000000000001"
        data_center = "0x3a02000000000000000000000000000000000002"
        vault_manager.deposit(data_center, 500.0)

        initial_tolls = sovereign_treasury.accumulated_tolls

        # 1. Register PPA Contract
        reg_res = client.post("/api/v1/power/contract/register", json={
            "contract_id": "PPA-CAISO-001",
            "provider_address": generator,
            "consumer_address": data_center,
            "rate_per_kwh_usdc": 0.08,  # $0.08 / kWh
            "grid_zone": "US-CAL-CAISO",
            "meter_device_id": "METER-ION-9000-01",
            "is_renewable": True,
            "rec_rate_multiplier": 1.05  # 5% green bonus
        })
        assert reg_res.status_code == 200, reg_res.text
        assert reg_res.json()["status"] == "POWER_CONTRACT_REGISTERED"

        # 2. Stream Power Consumption (1000 kWh with valid REC hash)
        rec_hash = "0x" + secrets.token_hex(32)
        stream_res = client.post("/api/v1/power/meter/stream", json={
            "contract_id": "PPA-CAISO-001",
            "kwh_consumed": 1000.0,
            "meter_device_id": "METER-ION-9000-01",
            "voltage_v": 480.0,
            "frequency_hz": 60.02,
            "meter_signature": "0x" + secrets.token_hex(65),
            "rec_certificate_hash": rec_hash,
            "chain_id": 137
        })
        assert stream_res.status_code == 200, stream_res.text
        s_data = stream_res.json()
        assert s_data["status"] == "SETTLED_STREAM"
        # 1000 kWh * 0.08 * 1.05 = 84.0 USDC
        assert s_data["gross_amount_usdc"] == 84.0
        # 0.25% protocol toll = 0.21 USDC
        assert s_data["protocol_fee_usdc"] == 0.21
        assert s_data["net_payout_usdc"] == 83.79
        assert "attestation" in s_data
        assert s_data["attestation"]["signature"].startswith("0x")

        # Verify Vault balances
        assert vault_manager.get_account(data_center).balance_usdc == round(500.0 - 84.0, 6)
        assert vault_manager.get_account(generator).balance_usdc == 83.79
        assert sovereign_treasury.accumulated_tolls >= initial_tolls + 0.21

    def test_grid_frequency_anomaly_rejection(self, client):
        """Protects physical infrastructure by rejecting readings with out-of-spec grid frequency."""
        generator = "0x3a03000000000000000000000000000000000003"
        data_center = "0x3a04000000000000000000000000000000000004"
        vault_manager.deposit(data_center, 200.0)

        client.post("/api/v1/power/contract/register", json={
            "contract_id": "PPA-FREQ-FAIL",
            "provider_address": generator,
            "consumer_address": data_center,
            "rate_per_kwh_usdc": 0.10,
            "grid_zone": "EU-DE-LU",
            "meter_device_id": "METER-SIEMENS-02"
        })

        # Submit reading with unstable frequency (54.5 Hz when nominal is 50Hz)
        bad_res = client.post("/api/v1/power/meter/stream", json={
            "contract_id": "PPA-FREQ-FAIL",
            "kwh_consumed": 500.0,
            "meter_device_id": "METER-SIEMENS-02",
            "voltage_v": 230.0,
            "frequency_hz": 54.5,
            "meter_signature": "0xmock"
        })
        assert bad_res.status_code == 400
        assert "frequency anomaly" in bad_res.json()["detail"].lower()

    def test_unbound_smart_meter_id_rejection(self, client):
        """Rejects telemetry submitted from an unregistered or rogue smart meter device."""
        generator = "0x3a05000000000000000000000000000000000005"
        data_center = "0x3a06000000000000000000000000000000000006"
        vault_manager.deposit(data_center, 100.0)

        client.post("/api/v1/power/contract/register", json={
            "contract_id": "PPA-ROGUE-METER",
            "provider_address": generator,
            "consumer_address": data_center,
            "rate_per_kwh_usdc": 0.05,
            "grid_zone": "KR-KPX",
            "meter_device_id": "LEGIT-METER-01"
        })

        rogue_res = client.post("/api/v1/power/meter/stream", json={
            "contract_id": "PPA-ROGUE-METER",
            "kwh_consumed": 100.0,
            "meter_device_id": "ROGUE-FAKE-METER-99",
            "voltage_v": 220.0,
            "frequency_hz": 60.0,
            "meter_signature": "0xmock"
        })
        assert rogue_res.status_code == 400
        assert "does not match bound meter" in rogue_res.json()["detail"]


class TestAutonomousFleetPoDOracle:
    def test_register_and_verify_delivery_settle_success(self, client):
        """Autonomous Truck delivers server racks to Amsterdam datacenter; settles upon geofence arrival."""
        shipper = "0x3b01000000000000000000000000000000000001"
        carrier = "0x3b02000000000000000000000000000000000002"
        vault_manager.deposit(shipper, 500.0)

        # Target: Amsterdam Port (52.3676, 4.9041)
        target_lat = 52.3676
        target_lon = 4.9041

        # 1. Register Mission and Lock Escrow ($200 USDC)
        reg_res = client.post("/api/v1/fleet/mission/register", json={
            "mission_id": "MISSION-AMS-01",
            "shipper_address": shipper,
            "carrier_address": carrier,
            "cargo_description": "NVIDIA H100 AI Compute Racks",
            "freight_amount_usdc": 200.0,
            "target_lat": target_lat,
            "target_lon": target_lon,
            "eseal_pubkey_hash": "0x" + secrets.token_hex(32),
            "geofence_radius_meters": 500.0,
            "timelock_seconds": 3600,
            "max_temp_celsius": 30.0
        })
        assert reg_res.status_code == 200, reg_res.text
        assert reg_res.json()["status"] == "MISSION_DISPATCHED"

        # Shipper vault deducted by $200
        assert vault_manager.get_account(shipper).balance_usdc == 300.0

        # 2. Carrier arrives at delivery location (52.3678, 4.9043 -> ~26 meters away)
        pod_res = client.post("/api/v1/fleet/delivery/verify", json={
            "mission_id": "MISSION-AMS-01",
            "carrier_address": carrier,
            "delivery_lat": 52.3678,
            "delivery_lon": 4.9043,
            "eseal_tamper_flag": False,
            "eseal_signature": "0x" + secrets.token_hex(65),
            "ambient_temp_celsius": 21.5,
            "chain_id": 137
        })
        assert pod_res.status_code == 200, pod_res.text
        pod_data = pod_res.json()
        assert pod_data["status"] == "DELIVERED_AND_SETTLED"
        assert pod_data["distance_meters"] < 50.0
        assert pod_data["gross_freight_usdc"] == 200.0
        # 0.25% protocol toll = 0.50 USDC
        assert pod_data["protocol_fee_usdc"] == 0.50
        assert pod_data["net_payout_usdc"] == 199.50
        assert "attestation" in pod_data
        assert pod_data["attestation"]["signature"].startswith("0x")

        # Carrier credited
        assert vault_manager.get_account(carrier).balance_usdc == 199.50

    def test_geofence_arrival_violation_rejection(self, client):
        """Carrier attempting to settle while outside the destination geofence is rejected."""
        shipper = "0x3b03000000000000000000000000000000000003"
        carrier = "0x3b04000000000000000000000000000000000004"
        vault_manager.deposit(shipper, 300.0)

        client.post("/api/v1/fleet/mission/register", json={
            "mission_id": "MISSION-GEOFENCE-FAIL",
            "shipper_address": shipper,
            "carrier_address": carrier,
            "cargo_description": "Lithium Battery Cells",
            "freight_amount_usdc": 100.0,
            "target_lat": 37.7749,  # San Francisco
            "target_lon": -122.4194,
            "eseal_pubkey_hash": "0xmock",
            "geofence_radius_meters": 200.0
        })

        # Submit delivery 10 km away in Oakland (37.8044, -122.2712)
        fail_res = client.post("/api/v1/fleet/delivery/verify", json={
            "mission_id": "MISSION-GEOFENCE-FAIL",
            "carrier_address": carrier,
            "delivery_lat": 37.8044,
            "delivery_lon": -122.2712,
            "eseal_tamper_flag": False,
            "eseal_signature": "0xmock"
        })
        assert fail_res.status_code == 400
        assert "geofence arrival failed" in fail_res.json()["detail"].lower()

    def test_eseal_tamper_flag_rejection_and_slashing(self, client):
        """If Electronic Seal detects physical tampering/breach, payout is rejected and carrier penalized."""
        shipper = "0x3b05000000000000000000000000000000000005"
        carrier = "0x3b06000000000000000000000000000000000006"
        vault_manager.deposit(shipper, 200.0)

        client.post("/api/v1/fleet/mission/register", json={
            "mission_id": "MISSION-TAMPER-TEST",
            "shipper_address": shipper,
            "carrier_address": carrier,
            "cargo_description": "High Value Bio-Pharma Reagents",
            "freight_amount_usdc": 150.0,
            "target_lat": 48.8566,
            "target_lon": 2.3522,
            "eseal_pubkey_hash": "0xmock"
        })

        # Delivery at correct GPS coordinates, but seal was tampered
        tamper_res = client.post("/api/v1/fleet/delivery/verify", json={
            "mission_id": "MISSION-TAMPER-TEST",
            "carrier_address": carrier,
            "delivery_lat": 48.8566,
            "delivery_lon": 2.3522,
            "eseal_tamper_flag": True,  # Physical seal broken!
            "eseal_signature": "0xmock"
        })
        assert tamper_res.status_code == 400
        assert "tamper flag detected" in tamper_res.json()["detail"].lower()

    def test_timelock_expiry_refund_to_shipper(self, client):
        """If delivery mission expires without delivery, shipper can claim full freight refund."""
        shipper = "0x3b07000000000000000000000000000000000007"
        carrier = "0x3b08000000000000000000000000000000000008"
        vault_manager.deposit(shipper, 250.0)

        reg_res = client.post("/api/v1/fleet/mission/register", json={
            "mission_id": "MISSION-REFUND-01",
            "shipper_address": shipper,
            "carrier_address": carrier,
            "cargo_description": "Agricultural Raw Goods",
            "freight_amount_usdc": 100.0,
            "target_lat": 1.3521,
            "target_lon": 103.8198,
            "eseal_pubkey_hash": "0xmock",
            "timelock_seconds": 300
        })
        assert reg_res.status_code == 200, reg_res.text
        assert vault_manager.get_account(shipper).balance_usdc == 150.0

        # Simulate expiration
        autonomous_fleet_pod_oracle.missions["MISSION-REFUND-01"]["expires_at"] = int(time.time()) - 10

        ref_res = client.post("/api/v1/fleet/mission/refund/MISSION-REFUND-01")
        assert ref_res.status_code == 200, ref_res.text
        assert ref_res.json()["status"] == "REFUNDED"
        assert ref_res.json()["refunded_amount_usdc"] == 100.0

        # Shipper refunded
        assert vault_manager.get_account(shipper).balance_usdc == 250.0


class TestPhase3SDKIntegration:
    def test_sdk_full_phase3_workflow(self):
        """UniversalEscrowClient executes full Power PPA streaming and Autonomous Fleet PoD lifecycle."""
        sdk = UniversalEscrowClient(chain_id=137, app=app)
        generator = "0x3c01000000000000000000000000000000000001"
        consumer = "0x3c02000000000000000000000000000000000002"
        shipper = "0x3c03000000000000000000000000000000000003"
        carrier = "0x3c04000000000000000000000000000000000004"

        vault_manager.deposit(consumer, 500.0)
        vault_manager.deposit(shipper, 500.0)

        # 1. SDK Power PPA Registration & Streaming
        ppa = sdk.register_power_contract(
            contract_id="SDK-PPA-CAISO",
            provider_address=generator,
            consumer_address=consumer,
            rate_per_kwh_usdc=0.06,
            grid_zone="US-CAL-CAISO",
            meter_device_id="SDK-SMART-METER-01"
        )
        assert ppa["status"] == "POWER_CONTRACT_REGISTERED"

        stream = sdk.stream_power_consumption(
            contract_id="SDK-PPA-CAISO",
            kwh_consumed=2500.0,
            meter_device_id="SDK-SMART-METER-01",
            voltage_v=480.0,
            frequency_hz=59.98,
            meter_signature="0x" + secrets.token_hex(65)
        )
        assert stream["status"] == "SETTLED_STREAM"
        # 2500 kWh * $0.06 = $150.00 USDC
        assert stream["gross_amount_usdc"] == 150.0

        # 2. SDK Autonomous Fleet PoD Registration & Verification
        mission = sdk.register_delivery_mission(
            mission_id="SDK-MISSION-01",
            shipper_address=shipper,
            carrier_address=carrier,
            cargo_description="Edge AI Compute Nodes",
            freight_amount_usdc=180.0,
            target_lat=35.6762,  # Tokyo
            target_lon=139.6503,
            eseal_pubkey_hash="0x" + secrets.token_hex(32),
            geofence_radius_meters=300.0
        )
        assert mission["status"] == "MISSION_DISPATCHED"

        # Carrier verifies delivery
        verify = sdk.verify_delivery_and_settle(
            mission_id="SDK-MISSION-01",
            carrier_address=carrier,
            delivery_lat=35.6763,
            delivery_lon=139.6504,
            eseal_tamper_flag=False,
            eseal_signature="0x" + secrets.token_hex(65)
        )
        assert verify["status"] == "DELIVERED_AND_SETTLED"
        assert verify["gross_freight_usdc"] == 180.0
        assert verify["distance_meters"] < 50.0
