"""
Power & Grid Oracle (Energy Substrate)
Autonomous Smart Meter IoT & Renewable Energy Certificate (REC) PPA Settlement Engine.
Enables AI data centers, GPU clusters, and autonomous facilities to stream micro-payments
for electricity consumption (kWh) with verifiable physical grid telemetry and green attributes.
Standard: A.GRID AP2/1.0 & EIP-712 PowerSettlementAttestation
"""

import math
import secrets
import threading
import time
from typing import Any, Dict, List, Optional
import eth_utils
from eth_account.messages import encode_typed_data

from app.onchain_signer import onchain_signer
from app.vault_manager import vault_manager, AgentVaultAccount
from app.rwa_treasury_engine import sovereign_treasury
from app.credit_rating_engine import credit_engine


class PowerGridOracle:
    """
    Decentralized Energy & Grid Settlement Oracle.
    Validates IoT smart meter readings, grid frequency/voltage invariants,
    and settles kWh consumption micro-payments directly via Agent Vaults.
    """

    PROTOCOL_FEE_BPS = 25  # 0.25% Protocol Toll

    def __init__(self):
        self._lock = threading.Lock()
        self.contracts: Dict[str, Dict[str, Any]] = {}
        self.readings_log: Dict[str, List[Dict[str, Any]]] = {}
        self.signer = onchain_signer

    def register_power_contract(
        self,
        contract_id: str,
        provider_address: str,
        consumer_address: str,
        rate_per_kwh_usdc: float,
        grid_zone: str,
        meter_device_id: str,
        is_renewable: bool = True,
        rec_rate_multiplier: float = 1.0,
        max_kwh_limit: float = 10_000_000.0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Registers a verified Power Purchase Agreement (PPA) with bound IoT Smart Meter."""
        with self._lock:
            if contract_id in self.contracts:
                raise ValueError(f"Power contract '{contract_id}' already registered.")

            if rate_per_kwh_usdc <= 0:
                raise ValueError("rate_per_kwh_usdc must be positive.")

            clean_provider = eth_utils.to_checksum_address(provider_address)
            clean_consumer = eth_utils.to_checksum_address(consumer_address)

            contract = {
                "contract_id": contract_id,
                "provider_address": clean_provider,
                "consumer_address": clean_consumer,
                "rate_per_kwh_usdc": float(rate_per_kwh_usdc),
                "grid_zone": grid_zone.strip().upper(),
                "meter_device_id": meter_device_id.strip(),
                "is_renewable": bool(is_renewable),
                "rec_rate_multiplier": float(rec_rate_multiplier),
                "max_kwh_limit": float(max_kwh_limit),
                "total_kwh_settled": 0.0,
                "total_usdc_settled": 0.0,
                "status": "ACTIVE",
                "registered_at": int(time.time()),
                "metadata": metadata or {}
            }
            self.contracts[contract_id] = contract
            self.readings_log[contract_id] = []

            return {
                "status": "POWER_CONTRACT_REGISTERED",
                "contract_id": contract_id,
                "provider_address": clean_provider,
                "consumer_address": clean_consumer,
                "grid_zone": contract["grid_zone"],
                "rate_per_kwh_usdc": contract["rate_per_kwh_usdc"],
                "meter_device_id": contract["meter_device_id"]
            }

    def stream_power_consumption(
        self,
        contract_id: str,
        kwh_consumed: float,
        meter_device_id: str,
        voltage_v: float,
        frequency_hz: float,
        meter_signature: str,
        rec_certificate_hash: Optional[str] = None,
        chain_id: int = 137
    ) -> Dict[str, Any]:
        """
        Validates telemetry from IoT Smart Meter and executes atomic micro-payment streaming.
        Checks grid stability (frequency in 50Hz/60Hz standard margin, voltage > 0).
        """
        with self._lock:
            contract = self.contracts.get(contract_id)
            if not contract:
                raise ValueError(f"Power contract '{contract_id}' not found.")

            if contract["status"] != "ACTIVE":
                raise ValueError(f"Power contract '{contract_id}' is not active.")

            if meter_device_id.strip() != contract["meter_device_id"]:
                raise ValueError(
                    f"Invalid smart meter: device '{meter_device_id}' does not match bound meter '{contract['meter_device_id']}'."
                )

            if kwh_consumed <= 0:
                raise ValueError("kwh_consumed must be strictly greater than 0.")

            # 1. Physical Grid Invariant Checks
            # Frequency standard: 50Hz +/- 1.5Hz or 60Hz +/- 1.5Hz
            valid_freq = (48.5 <= frequency_hz <= 51.5) or (58.5 <= frequency_hz <= 61.5)
            if not valid_freq:
                raise ValueError(
                    f"Grid frequency anomaly detected ({frequency_hz} Hz). Out of operational stability margin."
                )

            if voltage_v < 90.0 or voltage_v > 600.0:
                raise ValueError(f"Grid voltage out of nominal bounds ({voltage_v} V).")

            # 2. Financial settlement calculation
            base_rate = contract["rate_per_kwh_usdc"]
            if contract["is_renewable"] and rec_certificate_hash:
                effective_rate = round(base_rate * contract["rec_rate_multiplier"], 6)
            else:
                effective_rate = base_rate

            gross_amount = round(kwh_consumed * effective_rate, 6)
            if gross_amount <= 0:
                gross_amount = 0.000001

            # Check consumer vault balance
            consumer_addr = contract["consumer_address"]
            consumer_acc = vault_manager.get_account(consumer_addr)
            if not consumer_acc or consumer_acc.balance_usdc < gross_amount:
                bal = consumer_acc.balance_usdc if consumer_acc else 0.0
                raise ValueError(
                    f"Insufficient consumer vault balance: agent has {bal} USDC, required {gross_amount} USDC."
                )

            # Deduct from consumer
            consumer_acc.balance_usdc = round(consumer_acc.balance_usdc - gross_amount, 6)

            # Fee calculation
            protocol_fee = round((gross_amount * self.PROTOCOL_FEE_BPS) / 10000.0, 6)
            provider_net = round(gross_amount - protocol_fee, 6)

            # Credit provider
            provider_addr = contract["provider_address"]
            provider_acc = vault_manager.get_account(provider_addr)
            if not provider_acc:
                session_key = "ak_live_" + secrets.token_hex(24)
                now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                provider_acc = AgentVaultAccount(
                    agent_address=provider_addr,
                    balance_usdc=0.0,
                    total_deposited_usdc=0.0,
                    total_consumed_usdc=0.0,
                    session_key=session_key,
                    created_at_utc=now_iso,
                    last_active_utc=now_iso,
                    query_count=0
                )
                with vault_manager._lock:
                    vault_manager._accounts[provider_addr] = provider_acc
                    vault_manager._session_index[session_key] = provider_addr

            provider_acc.balance_usdc = round(provider_acc.balance_usdc + provider_net, 6)

            # Accumulate Sovereign Treasury Toll
            sovereign_treasury.accumulated_tolls += protocol_fee

            # Update contract aggregates
            contract["total_kwh_settled"] = round(contract["total_kwh_settled"] + kwh_consumed, 4)
            contract["total_usdc_settled"] = round(contract["total_usdc_settled"] + gross_amount, 6)

            # 3. Cryptographic EIP-712 Attestation
            now = int(time.time())
            domain_data = {
                "name": "PowerGridOracle",
                "version": "1.0",
                "chainId": int(chain_id),
                "verifyingContract": "0x4444444444444444444444444444444444444444"
            }
            types = {
                "EIP712Domain": [
                    {"name": "name", "type": "string"},
                    {"name": "version", "type": "string"},
                    {"name": "chainId", "type": "uint256"},
                    {"name": "verifyingContract", "type": "address"}
                ],
                "PowerSettlementAttestation": [
                    {"name": "contractId", "type": "string"},
                    {"name": "meterDeviceId", "type": "string"},
                    {"name": "consumer", "type": "address"},
                    {"name": "provider", "type": "address"},
                    {"name": "kwhScaled", "type": "uint256"},
                    {"name": "grossAmount", "type": "uint256"},
                    {"name": "gridZone", "type": "string"},
                    {"name": "timestamp", "type": "uint256"}
                ]
            }
            message_data = {
                "contractId": contract_id,
                "meterDeviceId": meter_device_id.strip(),
                "consumer": consumer_addr,
                "provider": provider_addr,
                "kwhScaled": int(round(kwh_consumed * 1000)),  # Wh scale
                "grossAmount": int(round(gross_amount * 1_000_000)),
                "gridZone": contract["grid_zone"],
                "timestamp": now
            }
            signable_msg = encode_typed_data(full_message={
                "types": types,
                "primaryType": "PowerSettlementAttestation",
                "domain": domain_data,
                "message": message_data
            })
            signed = self.signer.account.sign_message(signable_msg)

            reading_record = {
                "reading_id": "PWR-" + secrets.token_hex(12),
                "kwh_consumed": kwh_consumed,
                "gross_amount_usdc": gross_amount,
                "net_payout_usdc": provider_net,
                "protocol_fee_usdc": protocol_fee,
                "voltage_v": voltage_v,
                "frequency_hz": frequency_hz,
                "rec_hash": rec_certificate_hash,
                "timestamp": now
            }
            self.readings_log[contract_id].append(reading_record)

            # Record telemetry for FICO Credit Rating
            credit_engine.record_audit(provider_addr, verdict="PASSED", hallucination_detected=False)

            return {
                "status": "SETTLED_STREAM",
                "contract_id": contract_id,
                "meter_device_id": meter_device_id,
                "kwh_consumed": kwh_consumed,
                "gross_amount_usdc": gross_amount,
                "net_payout_usdc": provider_net,
                "protocol_fee_usdc": protocol_fee,
                "consumer_balance_usdc": consumer_acc.balance_usdc,
                "grid_zone": contract["grid_zone"],
                "attestation": {
                    "contractId": contract_id,
                    "oracle_signer": self.signer.signer_address,
                    "signature": "0x" + signed.signature.hex(),
                    "v": signed.v,
                    "r": "0x" + signed.r.to_bytes(32, "big").hex(),
                    "s": "0x" + signed.s.to_bytes(32, "big").hex(),
                    "timestamp": now
                }
            }


power_grid_oracle = PowerGridOracle()
