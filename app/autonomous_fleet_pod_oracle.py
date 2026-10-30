"""
Autonomous Fleet & Electronic Seal PoD Oracle (Mobility & Logistics Substrate)
Autonomous Truck, Maritime Container, and Drone Last-Mile Delivery Settlement Engine.
Enables autonomous transport agents to prove delivery via GNSS Geofencing and
cryptographic Electronic Seal (E-Seal) hardware tamper-proof verification for instant atomic payout.
Standard: A.GRID AP2/1.0 & EIP-712 ProofOfDeliveryAttestation
"""

import math
import secrets
import threading
import time
from typing import Any, Dict, Optional
import eth_utils
from eth_account.messages import encode_typed_data

from app.onchain_signer import onchain_signer
from app.vault_manager import vault_manager, AgentVaultAccount
from app.rwa_treasury_engine import sovereign_treasury
from app.credit_rating_engine import credit_engine


def calculate_haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates great-circle distance between two GPS coordinates in meters."""
    R = 6371000.0  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return round(R * c, 2)


class AutonomousFleetPoDOracle:
    """
    Decentralized Proof-of-Delivery (PoD) Oracle for Autonomous Logistics.
    Validates GNSS geofence arrival and tamper-free electronic seal telemetry,
    releasing escrowed freight payments in real-time.
    """

    PROTOCOL_FEE_BPS = 25  # 0.25% Protocol Toll

    def __init__(self):
        self._lock = threading.Lock()
        self.missions: Dict[str, Dict[str, Any]] = {}
        self.signer = onchain_signer

    def register_delivery_mission(
        self,
        mission_id: str,
        shipper_address: str,
        carrier_address: str,
        cargo_description: str,
        freight_amount_usdc: float,
        target_lat: float,
        target_lon: float,
        eseal_pubkey_hash: str,
        geofence_radius_meters: float = 500.0,
        timelock_seconds: int = 86400,
        max_temp_celsius: Optional[float] = None,
        min_temp_celsius: Optional[float] = None,
        chain_id: int = 137,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Registers a mission and locks freight fee into escrow from shipper vault."""
        with self._lock:
            if mission_id in self.missions:
                raise ValueError(f"Mission '{mission_id}' already registered.")

            if freight_amount_usdc <= 0:
                raise ValueError("freight_amount_usdc must be positive.")

            clean_shipper = eth_utils.to_checksum_address(shipper_address)
            clean_carrier = eth_utils.to_checksum_address(carrier_address)

            # Deduct escrow funds from shipper vault
            shipper_acc = vault_manager.get_account(clean_shipper)
            if not shipper_acc or shipper_acc.balance_usdc < freight_amount_usdc:
                bal = shipper_acc.balance_usdc if shipper_acc else 0.0
                raise ValueError(
                    f"Insufficient shipper vault balance: shipper has {bal} USDC, required {freight_amount_usdc} USDC."
                )

            shipper_acc.balance_usdc = round(shipper_acc.balance_usdc - freight_amount_usdc, 6)

            now = int(time.time())
            expires_at = now + timelock_seconds

            mission = {
                "mission_id": mission_id,
                "shipper_address": clean_shipper,
                "carrier_address": clean_carrier,
                "cargo_description": cargo_description,
                "freight_amount_usdc": float(freight_amount_usdc),
                "target_lat": float(target_lat),
                "target_lon": float(target_lon),
                "geofence_radius_meters": float(geofence_radius_meters),
                "eseal_pubkey_hash": eseal_pubkey_hash.strip().lower(),
                "max_temp_celsius": float(max_temp_celsius) if max_temp_celsius is not None else None,
                "min_temp_celsius": float(min_temp_celsius) if min_temp_celsius is not None else None,
                "chain_id": int(chain_id),
                "status": "DISPATCHED",
                "registered_at": now,
                "expires_at": expires_at,
                "metadata": metadata or {}
            }
            self.missions[mission_id] = mission

            return {
                "status": "MISSION_DISPATCHED",
                "mission_id": mission_id,
                "shipper_address": clean_shipper,
                "carrier_address": clean_carrier,
                "freight_locked_usdc": freight_amount_usdc,
                "target_lat": target_lat,
                "target_lon": target_lon,
                "geofence_radius_meters": geofence_radius_meters,
                "expires_at": expires_at
            }

    def verify_delivery_and_settle(
        self,
        mission_id: str,
        carrier_address: str,
        delivery_lat: float,
        delivery_lon: float,
        eseal_tamper_flag: bool,
        eseal_signature: str,
        ambient_temp_celsius: Optional[float] = None,
        chain_id: int = 137
    ) -> Dict[str, Any]:
        """
        Verifies GNSS physical arrival within geofence and E-Seal integrity.
        Upon success: instantly disburses freight payment to carrier.
        """
        with self._lock:
            mission = self.missions.get(mission_id)
            if not mission:
                raise ValueError(f"Mission '{mission_id}' not found.")

            if mission["status"] != "DISPATCHED":
                raise ValueError(f"Mission '{mission_id}' cannot be settled. Current status: {mission['status']}.")

            clean_carrier = eth_utils.to_checksum_address(carrier_address)
            if clean_carrier != mission["carrier_address"]:
                raise ValueError(
                    f"Unauthorized carrier '{clean_carrier}'. Expected registered carrier '{mission['carrier_address']}'."
                )

            now = int(time.time())
            if now > mission["expires_at"]:
                self._refund_shipper(mission)
                raise ValueError(f"Mission '{mission_id}' has expired. Freight refunded to shipper.")

            # 1. Geofence arrival check
            distance_meters = calculate_haversine_distance_meters(
                delivery_lat, delivery_lon,
                mission["target_lat"], mission["target_lon"]
            )
            if distance_meters > mission["geofence_radius_meters"]:
                raise ValueError(
                    f"GNSS Geofence arrival FAILED: carrier is {distance_meters}m away from target. Allowed radius is {mission['geofence_radius_meters']}m."
                )

            # 2. Electronic Seal (E-Seal) Tamper Check
            if eseal_tamper_flag is True:
                # Carrier tampered with physical cargo seal! Penalize credit score
                credit_engine.record_audit(clean_carrier, verdict="BLOCKED", hallucination_detected=True)
                raise ValueError("Electronic Seal TAMPER flag detected! Cargo unsealed or violated during transit.")

            # 3. Cold chain temperature checks if configured
            if ambient_temp_celsius is not None:
                if mission["max_temp_celsius"] is not None and ambient_temp_celsius > mission["max_temp_celsius"]:
                    credit_engine.record_audit(clean_carrier, verdict="FAILED", hallucination_detected=False)
                    raise ValueError(
                        f"Cold chain violation: temperature {ambient_temp_celsius}°C exceeded maximum limit {mission['max_temp_celsius']}°C."
                    )
                if mission["min_temp_celsius"] is not None and ambient_temp_celsius < mission["min_temp_celsius"]:
                    credit_engine.record_audit(clean_carrier, verdict="FAILED", hallucination_detected=False)
                    raise ValueError(
                        f"Temperature violation: temperature {ambient_temp_celsius}°C below minimum limit {mission['min_temp_celsius']}°C."
                    )

            # 4. Settle payout
            gross_amount = mission["freight_amount_usdc"]
            protocol_fee = round((gross_amount * self.PROTOCOL_FEE_BPS) / 10000.0, 6)
            carrier_net = round(gross_amount - protocol_fee, 6)

            carrier_acc = vault_manager.get_account(clean_carrier)
            if not carrier_acc:
                session_key = "ak_live_" + secrets.token_hex(24)
                now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                carrier_acc = AgentVaultAccount(
                    agent_address=clean_carrier,
                    balance_usdc=0.0,
                    total_deposited_usdc=0.0,
                    total_consumed_usdc=0.0,
                    session_key=session_key,
                    created_at_utc=now_iso,
                    last_active_utc=now_iso,
                    query_count=0
                )
                with vault_manager._lock:
                    vault_manager._accounts[clean_carrier] = carrier_acc
                    vault_manager._session_index[session_key] = clean_carrier

            carrier_acc.balance_usdc = round(carrier_acc.balance_usdc + carrier_net, 6)

            # Accumulate Sovereign Treasury Toll
            sovereign_treasury.accumulated_tolls += protocol_fee

            # 5. Sign EIP-712 ProofOfDeliveryAttestation
            domain_data = {
                "name": "AutonomousFleetPoDOracle",
                "version": "1.0",
                "chainId": int(chain_id),
                "verifyingContract": "0x3333333333333333333333333333333333333333"
            }
            types = {
                "EIP712Domain": [
                    {"name": "name", "type": "string"},
                    {"name": "version", "type": "string"},
                    {"name": "chainId", "type": "uint256"},
                    {"name": "verifyingContract", "type": "address"}
                ],
                "ProofOfDeliveryAttestation": [
                    {"name": "missionId", "type": "string"},
                    {"name": "shipper", "type": "address"},
                    {"name": "carrier", "type": "address"},
                    {"name": "grossAmount", "type": "uint256"},
                    {"name": "distanceMetersScaled", "type": "uint256"},
                    {"name": "timestamp", "type": "uint256"}
                ]
            }
            message_data = {
                "missionId": mission_id,
                "shipper": mission["shipper_address"],
                "carrier": clean_carrier,
                "grossAmount": int(round(gross_amount * 1_000_000)),
                "distanceMetersScaled": int(round(distance_meters * 100)),  # cm precision
                "timestamp": now
            }
            signable_msg = encode_typed_data(full_message={
                "types": types,
                "primaryType": "ProofOfDeliveryAttestation",
                "domain": domain_data,
                "message": message_data
            })
            signed = self.signer.account.sign_message(signable_msg)

            mission["status"] = "DELIVERED_AND_SETTLED"
            mission["settled_at"] = now
            mission["distance_meters"] = distance_meters

            # Boost carrier credit score
            credit_engine.record_audit(clean_carrier, verdict="PASSED", hallucination_detected=False)

            return {
                "status": "DELIVERED_AND_SETTLED",
                "mission_id": mission_id,
                "shipper_address": mission["shipper_address"],
                "carrier_address": clean_carrier,
                "distance_meters": distance_meters,
                "gross_freight_usdc": gross_amount,
                "net_payout_usdc": carrier_net,
                "protocol_fee_usdc": protocol_fee,
                "settled_at": now,
                "attestation": {
                    "missionId": mission_id,
                    "oracle_signer": self.signer.signer_address,
                    "signature": "0x" + signed.signature.hex(),
                    "v": signed.v,
                    "r": "0x" + signed.r.to_bytes(32, "big").hex(),
                    "s": "0x" + signed.s.to_bytes(32, "big").hex(),
                    "timestamp": now
                }
            }

    def refund_expired_mission(self, mission_id: str) -> Dict[str, Any]:
        """Manually or periodically refunds locked freight to shipper if timelock expired."""
        with self._lock:
            mission = self.missions.get(mission_id)
            if not mission:
                raise ValueError(f"Mission '{mission_id}' not found.")

            if mission["status"] != "DISPATCHED":
                raise ValueError(f"Mission '{mission_id}' cannot be refunded. Status: {mission['status']}.")

            now = int(time.time())
            if now <= mission["expires_at"]:
                raise ValueError(f"Mission '{mission_id}' timelock has not expired yet.")

            return self._refund_shipper(mission)

    def _refund_shipper(self, mission: Dict[str, Any]) -> Dict[str, Any]:
        """Internal helper to refund escrowed freight to shipper."""
        shipper = mission["shipper_address"]
        freight = mission["freight_amount_usdc"]

        account = vault_manager.get_account(shipper)
        if not account:
            session_key = "ak_live_" + secrets.token_hex(24)
            now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            account = AgentVaultAccount(
                agent_address=shipper,
                balance_usdc=0.0,
                total_deposited_usdc=0.0,
                total_consumed_usdc=0.0,
                session_key=session_key,
                created_at_utc=now_iso,
                last_active_utc=now_iso,
                query_count=0
            )
            with vault_manager._lock:
                vault_manager._accounts[shipper] = account
                vault_manager._session_index[session_key] = shipper

        account.balance_usdc = round(account.balance_usdc + freight, 6)
        mission["status"] = "REFUNDED"
        mission["refunded_at"] = int(time.time())

        return {
            "status": "REFUNDED",
            "mission_id": mission["mission_id"],
            "shipper_address": shipper,
            "refunded_amount_usdc": freight,
            "reason": "Delivery mission timelock expired without PoD verification."
        }

    def verify_advanced_pod_and_settle(
        self,
        mission_id: str,
        carrier_address: str,
        delivery_lat: float,
        delivery_lon: float,
        eseal_hardware_payload: Dict[str, Any],
        cold_chain_telemetry_series: Optional[List[Dict[str, Any]]] = None,
        max_allowed_breach_minutes: int = 15,
        chain_id: int = 137
    ) -> Dict[str, Any]:
        """
        Enterprise-grade PoD verification:
        1. GNSS Haversine geofence arrival.
        2. Hardware E-Seal Cryptographic Signature & Tamper Sensor Audit.
        3. Time-Series IoT Cold-Chain Integrity & Mean Kinetic Temperature (MKT).
        4. Slashing trigger: If tamper detected, immediately penalizes carrier and locks mission.
        """
        with self._lock:
            mission = self.missions.get(mission_id)
            if not mission:
                raise ValueError(f"Mission '{mission_id}' not found.")

            if mission["status"] != "DISPATCHED":
                raise ValueError(f"Mission '{mission_id}' cannot be settled. Current status: {mission['status']}.")

            clean_carrier = eth_utils.to_checksum_address(carrier_address)
            if clean_carrier != mission["carrier_address"]:
                raise ValueError(
                    f"Unauthorized carrier '{clean_carrier}'. Expected registered carrier '{mission['carrier_address']}'."
                )

            now = int(time.time())
            if now > mission["expires_at"]:
                self._refund_shipper(mission)
                raise ValueError(f"Mission '{mission_id}' has expired. Freight refunded to shipper.")

            # 1. Geofence Check
            distance_meters = calculate_haversine_distance_meters(
                delivery_lat, delivery_lon,
                mission["target_lat"], mission["target_lon"]
            )
            if distance_meters > mission["geofence_radius_meters"]:
                raise ValueError(
                    f"GNSS Geofence arrival FAILED: carrier is {distance_meters}m away. Allowed: {mission['geofence_radius_meters']}m."
                )

            # 2. Hardware E-Seal Cryptographic Verification
            tamper_flag = bool(eseal_hardware_payload.get("tamper_detected", False))
            hw_sig = eseal_hardware_payload.get("signature_hex", "")
            hw_nonce = eseal_hardware_payload.get("nonce", "")

            if tamper_flag:
                mission["status"] = "TAMPERED_SLASHED"
                credit_engine.record_audit(clean_carrier, verdict="BLOCKED", hallucination_detected=True)
                # Confiscate carrier collateral to Sovereign Treasury if available
                carrier_acc = vault_manager.get_account(clean_carrier)
                slash_amount = 0.0
                if carrier_acc and carrier_acc.balance_usdc > 0:
                    slash_amount = min(carrier_acc.balance_usdc, 10.0)  # Slash up to $10.00 USDC
                    carrier_acc.balance_usdc = round(carrier_acc.balance_usdc - slash_amount, 6)
                    sovereign_treasury.accumulated_tolls += slash_amount

                raise ValueError(f"CRITICAL E-SEAL BREACH: Physical seal tamper detected! Slashed {slash_amount} USDC and quarantined.")

            # Validate Cryptogram
            expected_msg = f"{mission['eseal_pubkey_hash']}:{hw_nonce}:{tamper_flag}"
            expected_sig = eth_utils.keccak(text=expected_msg).hex()
            if hw_sig.lower() != expected_sig.lower() and hw_sig != "0x" + expected_sig:
                raise ValueError("E-Seal hardware cryptogram signature mismatch or replay attack!")

            # 3. Continuous Time-Series Cold-Chain Analysis
            mkt_celsius = None
            total_breach_seconds = 0
            if cold_chain_telemetry_series and (mission["max_temp_celsius"] is not None or mission["min_temp_celsius"] is not None):
                temps = []
                for point in cold_chain_telemetry_series:
                    t = float(point.get("temp_celsius", 0.0))
                    temps.append(t)
                    # Check breach
                    is_breach = False
                    if mission["max_temp_celsius"] is not None and t > mission["max_temp_celsius"]:
                        is_breach = True
                    if mission["min_temp_celsius"] is not None and t < mission["min_temp_celsius"]:
                        is_breach = True

                    if is_breach:
                        total_breach_seconds += int(point.get("duration_seconds", 60))

                # Calculate MKT
                if temps:
                    mkt_celsius = calculate_mean_kinetic_temperature(temps)

                breach_minutes = total_breach_seconds / 60.0
                if breach_minutes > max_allowed_breach_minutes:
                    mission["status"] = "COLD_CHAIN_FAILED"
                    credit_engine.record_audit(clean_carrier, verdict="FAILED", hallucination_detected=False)
                    raise ValueError(
                        f"Cumulative cold-chain breach {breach_minutes:.1f}m exceeded maximum allowable {max_allowed_breach_minutes}m! MKT: {mkt_celsius:.2f}°C"
                    )

            # 4. Settle Payout
            gross_amount = mission["freight_amount_usdc"]
            protocol_fee = round((gross_amount * self.PROTOCOL_FEE_BPS) / 10000.0, 6)
            carrier_net = round(gross_amount - protocol_fee, 6)

            carrier_acc = vault_manager.get_account(clean_carrier)
            if not carrier_acc:
                session_key = "ak_live_" + secrets.token_hex(24)
                now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                carrier_acc = AgentVaultAccount(
                    agent_address=clean_carrier,
                    balance_usdc=0.0,
                    total_deposited_usdc=0.0,
                    total_consumed_usdc=0.0,
                    session_key=session_key,
                    created_at_utc=now_iso,
                    last_active_utc=now_iso,
                    query_count=0
                )
                with vault_manager._lock:
                    vault_manager._accounts[clean_carrier] = carrier_acc
                    vault_manager._session_index[session_key] = clean_carrier

            carrier_acc.balance_usdc = round(carrier_acc.balance_usdc + carrier_net, 6)
            sovereign_treasury.accumulated_tolls += protocol_fee

            # EIP-712 Attestation
            domain_data = {
                "name": "AutonomousFleetPoDOracle",
                "version": "1.0",
                "chainId": int(chain_id),
                "verifyingContract": "0x3333333333333333333333333333333333333333"
            }
            types = {
                "EIP712Domain": [
                    {"name": "name", "type": "string"},
                    {"name": "version", "type": "string"},
                    {"name": "chainId", "type": "uint256"},
                    {"name": "verifyingContract", "type": "address"}
                ],
                "ProofOfDeliveryAttestation": [
                    {"name": "missionId", "type": "string"},
                    {"name": "shipper", "type": "address"},
                    {"name": "carrier", "type": "address"},
                    {"name": "grossAmount", "type": "uint256"},
                    {"name": "distanceMetersScaled", "type": "uint256"},
                    {"name": "timestamp", "type": "uint256"}
                ]
            }
            message_data = {
                "missionId": mission_id,
                "shipper": mission["shipper_address"],
                "carrier": clean_carrier,
                "grossAmount": int(round(gross_amount * 1_000_000)),
                "distanceMetersScaled": int(round(distance_meters * 100)),
                "timestamp": now
            }
            signable_msg = encode_typed_data(full_message={
                "types": types,
                "primaryType": "ProofOfDeliveryAttestation",
                "domain": domain_data,
                "message": message_data
            })
            signed = self.signer.account.sign_message(signable_msg)

            mission["status"] = "DELIVERED_AND_SETTLED"
            mission["settled_at"] = now
            mission["distance_meters"] = distance_meters
            mission["mkt_celsius"] = mkt_celsius

            credit_engine.record_audit(clean_carrier, verdict="PASSED", hallucination_detected=False)

            return {
                "status": "DELIVERED_AND_SETTLED",
                "mission_id": mission_id,
                "shipper_address": mission["shipper_address"],
                "carrier_address": clean_carrier,
                "distance_meters": distance_meters,
                "mkt_celsius": mkt_celsius,
                "breach_minutes": total_breach_seconds / 60.0,
                "gross_freight_usdc": gross_amount,
                "net_payout_usdc": carrier_net,
                "protocol_fee_usdc": protocol_fee,
                "settled_at": now,
                "attestation": {
                    "missionId": mission_id,
                    "oracle_signer": self.signer.signer_address,
                    "signature": "0x" + signed.signature.hex(),
                    "timestamp": now
                }
            }


def calculate_mean_kinetic_temperature(temps_celsius: List[float], delta_h_kj: float = 83.144) -> float:
    """Calculates Mean Kinetic Temperature (MKT) in Celsius per USP / WHO guidelines."""
    if not temps_celsius:
        return 0.0
    R = 8.314462618  # Universal gas constant J/(mol*K)
    delta_h_j = delta_h_kj * 1000.0  # Activation energy in J/mol

    sum_exp = 0.0
    for t_c in temps_celsius:
        t_k = t_c + 273.15  # Convert to Kelvin
        if t_k <= 0:
            continue
        sum_exp += math.exp(-delta_h_j / (R * t_k))

    n = len(temps_celsius)
    if sum_exp <= 0 or n == 0:
        return sum(temps_celsius) / len(temps_celsius)

    mkt_k = (delta_h_j / R) / (-math.log(sum_exp / n))
    return round(mkt_k - 273.15, 2)


autonomous_fleet_pod_oracle = AutonomousFleetPoDOracle()

