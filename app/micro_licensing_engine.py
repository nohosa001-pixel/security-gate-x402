"""
Micro-Licensing Engine - Per-Query & Per-Weight Streaming Settlement.
====================================================================
Provides fine-grained, machine-to-machine licensing rails for:
1. Per-query knowledge API consumption (CleanWeb, Bio/Chemical queries).
2. Per-weight / per-shard AI model weight streaming (LoRA adapters, checkpoints).
3. Per-token / per-step synthetic inference streaming.

Protocol Characteristics:
- Automatic micro-billing deducted from Vault / pre-funded state channels.
- Capability token issuance (HMAC/EIP-712 Access Tokens) preventing unauthorized access.
- 0.25% clearing toll accumulated directly to Sovereign RWA Treasury.
"""

import time
import secrets
import hmac
import hashlib
from typing import Dict, Any, Optional
import eth_utils
from eth_account.messages import encode_typed_data

from app.onchain_signer import onchain_signer
from app.rwa_treasury_engine import sovereign_treasury
from app.vault_manager import vault_manager
from app.credit_rating_engine import credit_engine


VALID_RATE_TYPES = {
    "PER_QUERY",
    "PER_WEIGHT_MB",
    "PER_INFERENCE_STEP"
}


class MicroLicensingEngine:
    """Manages fine-grained micro-licensing tariffs, capability tokens, and usage metering."""

    PROTOCOL_FEE_BPS = 25  # 0.25% standard clearing fee

    def __init__(self, signer=None):
        self.signer = signer or onchain_signer
        # Tariffs: asset_id -> tariff_config
        self.tariffs: Dict[str, Dict[str, Any]] = {}
        # Active capability tokens: token_id -> token_record
        self.tokens: Dict[str, Dict[str, Any]] = {}
        # Signing secret for HMAC capability tickets
        self._hmac_secret = secrets.token_bytes(32)

    def register_licensing_tariff(
        self,
        asset_id: str,
        provider_address: str,
        rate_type: str,
        price_per_unit_usdc: float,
        min_units: int = 1,
        max_units_per_order: int = 1_000_000,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Registers an asset tariff for micro-licensing (e.g. $0.0005 per query, $0.002 per MB).
        """
        clean_provider = eth_utils.to_checksum_address(provider_address)
        clean_type = rate_type.upper().strip()
        if clean_type not in VALID_RATE_TYPES:
            raise ValueError(f"Invalid rate_type '{clean_type}'. Must be one of {sorted(VALID_RATE_TYPES)}")

        if price_per_unit_usdc <= 0.0:
            raise ValueError("price_per_unit_usdc must be strictly positive.")

        tariff = {
            "asset_id": asset_id,
            "provider_address": clean_provider,
            "rate_type": clean_type,
            "price_per_unit_usdc": float(price_per_unit_usdc),
            "min_units": int(min_units),
            "max_units_per_order": int(max_units_per_order),
            "metadata": metadata or {},
            "registered_at": int(time.time()),
            "status": "ACTIVE"
        }
        self.tariffs[asset_id] = tariff

        return {
            "status": "TARIFF_REGISTERED",
            "asset_id": asset_id,
            "provider_address": clean_provider,
            "rate_type": clean_type,
            "price_per_unit_usdc": float(price_per_unit_usdc)
        }

    def purchase_license_quota(
        self,
        asset_id: str,
        consumer_address: str,
        units_requested: int,
        chain_id: int = 137,
        validity_seconds: int = 86400
    ) -> Dict[str, Any]:
        """
        Purchases a micro-licensing quota.
        Deducts cost from consumer's vault balance, disburses to provider,
        and generates a verifiable capability access token.
        """
        tariff = self.tariffs.get(asset_id)
        if not tariff or tariff["status"] != "ACTIVE":
            raise ValueError(f"Active licensing tariff not found for asset '{asset_id}'.")

        clean_consumer = eth_utils.to_checksum_address(consumer_address)
        if units_requested < tariff["min_units"]:
            raise ValueError(f"units_requested ({units_requested}) below minimum {tariff['min_units']}.")

        if units_requested > tariff["max_units_per_order"]:
            raise ValueError(f"units_requested ({units_requested}) exceeds maximum {tariff['max_units_per_order']}.")

        total_cost = round(units_requested * tariff["price_per_unit_usdc"], 6)

        # 1. Deduct cost from consumer vault
        consumer_acc = vault_manager.get_account(clean_consumer)
        if not consumer_acc or consumer_acc.balance_usdc < total_cost:
            bal = consumer_acc.balance_usdc if consumer_acc else 0.0
            raise ValueError(
                f"Insufficient vault balance: consumer has {bal} USDC, required {total_cost} USDC."
            )

        consumer_acc.balance_usdc = round(consumer_acc.balance_usdc - total_cost, 6)

        # 2. Payout to provider & protocol fee
        protocol_fee = round((total_cost * self.PROTOCOL_FEE_BPS) / 10000.0, 6)
        provider_net = round(total_cost - protocol_fee, 6)

        provider_acc = vault_manager.get_account(tariff["provider_address"])
        if not provider_acc:
            session_key = "ak_live_" + secrets.token_hex(24)
            now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            from app.vault_manager import AgentVaultAccount
            provider_acc = AgentVaultAccount(
                agent_address=tariff["provider_address"],
                balance_usdc=0.0,
                total_deposited_usdc=0.0,
                total_consumed_usdc=0.0,
                session_key=session_key,
                created_at_utc=now_iso,
                last_active_utc=now_iso,
                query_count=0
            )
            with vault_manager._lock:
                vault_manager._accounts[tariff["provider_address"]] = provider_acc
                vault_manager._session_index[session_key] = tariff["provider_address"]

        provider_acc.balance_usdc = round(provider_acc.balance_usdc + provider_net, 6)

        # Accumulate protocol fee
        sovereign_treasury.accumulated_tolls += protocol_fee

        # 3. Generate Capability Access Token
        now = int(time.time())
        expires_at = now + validity_seconds
        token_id = "MLT-" + secrets.token_hex(16)

        # HMAC capability signature
        msg_payload = f"{token_id}:{asset_id}:{clean_consumer}:{units_requested}:{expires_at}".encode("utf-8")
        signature = hmac.new(self._hmac_secret, msg_payload, hashlib.sha256).hexdigest()

        token_record = {
            "token_id": token_id,
            "asset_id": asset_id,
            "provider_address": tariff["provider_address"],
            "consumer_address": clean_consumer,
            "rate_type": tariff["rate_type"],
            "units_authorized": int(units_requested),
            "units_remaining": int(units_requested),
            "units_consumed": 0,
            "expires_at": expires_at,
            "issued_at": now,
            "signature": signature,
            "chain_id": int(chain_id),
            "total_paid_usdc": total_cost,
            "status": "ACTIVE"
        }
        self.tokens[token_id] = token_record

        # Sign EIP-712 MicroLicenseAttestation
        domain_data = {
            "name": "MicroLicensingEngine",
            "version": "1.0.0",
            "chainId": int(chain_id),
            "verifyingContract": "0x4Dbd77F4799816859a595f24a57A786516D2EAa8"
        }
        types = {
            "EIP712Domain": [
                {"name": "name", "type": "string"},
                {"name": "version", "type": "string"},
                {"name": "chainId", "type": "uint256"},
                {"name": "verifyingContract", "type": "address"}
            ],
            "MicroLicenseAttestation": [
                {"name": "tokenId", "type": "string"},
                {"name": "assetId", "type": "string"},
                {"name": "consumer", "type": "address"},
                {"name": "unitsAuthorized", "type": "uint256"},
                {"name": "expiresAt", "type": "uint256"}
            ]
        }
        message_data = {
            "tokenId": token_id,
            "assetId": asset_id,
            "consumer": clean_consumer,
            "unitsAuthorized": int(units_requested),
            "expiresAt": expires_at
        }
        signable_msg = encode_typed_data(full_message={
            "types": types,
            "primaryType": "MicroLicenseAttestation",
            "domain": domain_data,
            "message": message_data
        })
        signed = self.signer.account.sign_message(signable_msg)

        return {
            "status": "ISSUED",
            "token_id": token_id,
            "asset_id": asset_id,
            "consumer_address": clean_consumer,
            "provider_address": tariff["provider_address"],
            "rate_type": tariff["rate_type"],
            "units_authorized": int(units_requested),
            "total_paid_usdc": total_cost,
            "protocol_fee_usdc": protocol_fee,
            "expires_at": expires_at,
            "capability_token": f"bearer_{token_id}_{signature[:16]}",
            "attestation": {
                "tokenId": token_id,
                "assetId": asset_id,
                "signature": "0x" + signed.signature.hex(),
                "oracle_signer": self.signer.signer_address,
                "v": signed.v,
                "r": "0x" + signed.r.to_bytes(32, "big").hex(),
                "s": "0x" + signed.s.to_bytes(32, "big").hex()
            }
        }

    def meter_usage(
        self,
        token_id: str,
        units_consumed: int
    ) -> Dict[str, Any]:
        """
        Validates access token and decrements remaining licensed units in real time.
        """
        token = self.tokens.get(token_id)
        if not token:
            raise ValueError(f"License token '{token_id}' not found.")

        if token["status"] != "ACTIVE":
            raise ValueError(f"License token '{token_id}' is not active ({token['status']}).")

        now = int(time.time())
        if now > token["expires_at"]:
            token["status"] = "EXPIRED"
            raise ValueError(f"License token '{token_id}' has expired.")

        if units_consumed <= 0:
            raise ValueError("units_consumed must be strictly positive.")

        if token["units_remaining"] < units_consumed:
            raise ValueError(
                f"Quota exceeded: remaining {token['units_remaining']} units, requested {units_consumed} units."
            )

        token["units_remaining"] -= units_consumed
        token["units_consumed"] += units_consumed

        if token["units_remaining"] == 0:
            token["status"] = "EXHAUSTED"

        return {
            "status": "METERED",
            "token_id": token_id,
            "asset_id": token["asset_id"],
            "units_consumed_this_call": int(units_consumed),
            "total_consumed": token["units_consumed"],
            "units_remaining": token["units_remaining"],
            "is_exhausted": token["units_remaining"] == 0
        }


micro_licensing_engine = MicroLicensingEngine()
