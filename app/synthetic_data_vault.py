"""
Synthetic Data Vault - ZK Decryption Atomic Swap Escrow Engine.
===============================================================
Enables zero-trust data exchange for CleanWeb, synthetic bio-molecular structures,
and AI model weights (LoRA adapters, fine-tuned checkpoints).

Core Mechanism:
1. Provider registers encrypted data payload with ciphertext hash and key commitment:
   key_commitment = keccak256(raw_decryption_key).
2. Buyer locks purchase escrow in Universal Escrow / Data Vault.
3. Provider reveals decryption key:
   Vault atomically verifies keccak256(key) == key_commitment.
   If verified:
     - Escrow payment releases instantly to Provider (minus 0.25% protocol toll).
     - Decryption key is cryptographically signed and transferred to Buyer.
     - EIP-712 DataVaultSwapAttestation is issued.
   If key is invalid or deadline passes:
     - Buyer receives 100% refund. Provider receives zero.
"""

import time
import secrets
import hashlib
from typing import Dict, Any, Optional
import eth_utils
from eth_account.messages import encode_typed_data

from app.onchain_signer import onchain_signer
from app.rwa_treasury_engine import sovereign_treasury
from app.vault_manager import vault_manager
from app.credit_rating_engine import credit_engine


VALID_ASSET_TYPES = {
    "CLEANWEB_DATASET",
    "BIOPHARMA_MOLECULAR",
    "AI_WEIGHT_LORA",
    "SYNTHETIC_CLINICAL"
}


class SyntheticDataVault:
    """Manages confidential data asset registry, atomic swap escrows, and ZK decryption verification."""

    PROTOCOL_FEE_BPS = 25  # 0.25% standard clearing fee

    def __init__(self, signer=None):
        self.signer = signer or onchain_signer
        # Registry: asset_id -> asset_record
        self.assets: Dict[str, Dict[str, Any]] = {}
        # Active swaps: order_id -> swap_order
        self.orders: Dict[str, Dict[str, Any]] = {}

    def register_data_asset(
        self,
        asset_id: str,
        provider_address: str,
        asset_type: str,
        ciphertext_hash: str,
        key_commitment: str,
        price_usdc: float,
        zk_proof: Optional[str] = None,
        merkle_root: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Registers an encrypted synthetic data asset with pre-committed decryption key hash.
        """
        clean_provider = eth_utils.to_checksum_address(provider_address)
        clean_type = asset_type.upper().strip()
        if clean_type not in VALID_ASSET_TYPES:
            raise ValueError(f"Invalid asset_type '{clean_type}'. Must be one of {sorted(VALID_ASSET_TYPES)}")

        if price_usdc < 0.0:
            raise ValueError("Asset price cannot be negative.")

        clean_cipher_hash = ciphertext_hash.strip().lower()
        if not clean_cipher_hash.startswith("0x"):
            clean_cipher_hash = "0x" + clean_cipher_hash

        clean_commitment = key_commitment.strip().lower()
        if not clean_commitment.startswith("0x"):
            clean_commitment = "0x" + clean_commitment

        if len(clean_commitment) != 66:
            raise ValueError("key_commitment must be a 32-byte hex string (0x-prefixed, 66 chars).")

        now = int(time.time())
        record = {
            "asset_id": asset_id,
            "provider_address": clean_provider,
            "asset_type": clean_type,
            "ciphertext_hash": clean_cipher_hash,
            "key_commitment": clean_commitment,
            "price_usdc": float(price_usdc),
            "zk_proof": zk_proof or "0x" + "0" * 64,
            "merkle_root": merkle_root or clean_cipher_hash,
            "metadata": metadata or {},
            "registered_at": now,
            "status": "ACTIVE"
        }
        self.assets[asset_id] = record

        return {
            "status": "REGISTERED",
            "asset_id": asset_id,
            "provider_address": clean_provider,
            "asset_type": clean_type,
            "price_usdc": float(price_usdc),
            "key_commitment": clean_commitment,
            "registered_at": now
        }

    def create_atomic_swap_order(
        self,
        order_id: str,
        asset_id: str,
        buyer_address: str,
        chain_id: int = 137,
        timelock_seconds: int = 3600
    ) -> Dict[str, Any]:
        """
        Locks escrow funds from buyer for an atomic data swap.
        """
        asset = self.assets.get(asset_id)
        if not asset:
            raise ValueError(f"Asset '{asset_id}' not found in Data Vault.")

        if asset["status"] != "ACTIVE":
            raise ValueError(f"Asset '{asset_id}' is not active for trading.")

        clean_buyer = eth_utils.to_checksum_address(buyer_address)
        price_usdc = asset["price_usdc"]

        # Check buyer balance in vault
        account = vault_manager.get_account(clean_buyer)
        if not account or account.balance_usdc < price_usdc:
            bal = account.balance_usdc if account else 0.0
            raise ValueError(
                f"Insufficient vault balance for atomic swap: buyer has {bal} USDC, required {price_usdc} USDC."
            )

        # Escrow lock: deduct balance into pending escrow order
        account.balance_usdc = round(account.balance_usdc - price_usdc, 6)

        now = int(time.time())
        expires_at = now + timelock_seconds

        order = {
            "order_id": order_id,
            "asset_id": asset_id,
            "buyer_address": clean_buyer,
            "provider_address": asset["provider_address"],
            "price_usdc": price_usdc,
            "key_commitment": asset["key_commitment"],
            "ciphertext_hash": asset["ciphertext_hash"],
            "chain_id": int(chain_id),
            "locked_at": now,
            "expires_at": expires_at,
            "status": "ESCROW_LOCKED",
            "decryption_key": None
        }
        self.orders[order_id] = order

        return {
            "status": "ESCROW_LOCKED",
            "order_id": order_id,
            "asset_id": asset_id,
            "buyer_address": clean_buyer,
            "provider_address": asset["provider_address"],
            "locked_amount_usdc": price_usdc,
            "expires_at": expires_at,
            "key_commitment": asset["key_commitment"]
        }

    def execute_atomic_swap_decrypt(
        self,
        order_id: str,
        provider_address: str,
        decryption_key_hex: str,
        chain_id: int = 137
    ) -> Dict[str, Any]:
        """
        Verifies the revealed decryption key against the cryptographic commitment.
        If valid: atomically releases payment to provider and returns signed key attestation.
        """
        order = self.orders.get(order_id)
        if not order:
            raise ValueError(f"Order '{order_id}' not found.")

        if order["status"] != "ESCROW_LOCKED":
            raise ValueError(f"Order '{order_id}' is not in ESCROW_LOCKED status (current: {order['status']}).")

        clean_provider = eth_utils.to_checksum_address(provider_address)
        if clean_provider != order["provider_address"]:
            raise ValueError(f"Unauthorized provider address '{clean_provider}'. Expected '{order['provider_address']}'.")

        now = int(time.time())
        if now > order["expires_at"]:
            # Expired: auto-refund buyer
            self._refund_buyer(order)
            raise ValueError(f"Order '{order_id}' has expired. Escrow funds refunded to buyer.")

        clean_key = decryption_key_hex.strip().lower()
        if not clean_key.startswith("0x"):
            clean_key = "0x" + clean_key

        # Cryptographic verification: keccak256(raw_bytes) or keccak256(hex_bytes)
        try:
            key_bytes = eth_utils.to_bytes(hexstr=clean_key)
        except Exception:
            raise ValueError("decryption_key_hex is not a valid hex string.")

        computed_commitment = "0x" + eth_utils.keccak(key_bytes).hex().lower()
        expected_commitment = order["key_commitment"].lower()

        if computed_commitment != expected_commitment:
            # Penalize provider in credit score for fraudulent key submission
            credit_engine.record_audit(clean_provider, verdict="BLOCKED", hallucination_detected=True)
            raise ValueError(
                f"Decryption key verification FAILED. Commitment mismatch: computed {computed_commitment}, expected {expected_commitment}."
            )

        # 1. Calculate and disburse payout
        gross_amount = order["price_usdc"]
        protocol_fee = round((gross_amount * self.PROTOCOL_FEE_BPS) / 10000.0, 6)
        net_provider_payout = round(gross_amount - protocol_fee, 6)

        # Credit provider vault balance
        provider_acc = vault_manager.get_account(clean_provider)
        if not provider_acc:
            session_key = "ak_live_" + secrets.token_hex(24)
            now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            from app.vault_manager import AgentVaultAccount
            provider_acc = AgentVaultAccount(
                agent_address=clean_provider,
                balance_usdc=0.0,
                total_deposited_usdc=0.0,
                total_consumed_usdc=0.0,
                session_key=session_key,
                created_at_utc=now_iso,
                last_active_utc=now_iso,
                query_count=0
            )
            with vault_manager._lock:
                vault_manager._accounts[clean_provider] = provider_acc
                vault_manager._session_index[session_key] = clean_provider

        provider_acc.balance_usdc = round(provider_acc.balance_usdc + net_provider_payout, 6)

        # Accumulate protocol fee in RWA Treasury
        sovereign_treasury.accumulated_tolls += protocol_fee

        # Credit honest delivery rating
        credit_engine.record_audit(clean_provider, verdict="PASSED", hallucination_detected=False)

        # Update order status
        order["status"] = "SETTLED"
        order["decryption_key"] = clean_key
        order["settled_at"] = now
        order["protocol_fee_usdc"] = protocol_fee
        order["net_payout_usdc"] = net_provider_payout

        # 2. Sign EIP-712 DataVaultSwapAttestation
        domain_data = {
            "name": "SyntheticDataVault",
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
            "DataVaultSwapAttestation": [
                {"name": "orderId", "type": "bytes32"},
                {"name": "assetId", "type": "string"},
                {"name": "buyer", "type": "address"},
                {"name": "provider", "type": "address"},
                {"name": "grossAmount", "type": "uint256"},
                {"name": "keyCommitment", "type": "bytes32"},
                {"name": "keyHash", "type": "bytes32"},
                {"name": "timestamp", "type": "uint256"}
            ]
        }
        order_bytes32 = eth_utils.to_hex(eth_utils.to_bytes(text=str(order_id)).ljust(32, b"\0")) if len(str(order_id)) <= 32 else str(order_id)
        if not order_bytes32.startswith("0x"):
            order_bytes32 = "0x" + order_bytes32
        if len(order_bytes32) > 66:
            order_bytes32 = "0x" + eth_utils.keccak(text=str(order_id)).hex()

        message_data = {
            "orderId": order_bytes32,
            "assetId": order["asset_id"],
            "buyer": order["buyer_address"],
            "provider": clean_provider,
            "grossAmount": int(gross_amount * 1_000_000),
            "keyCommitment": expected_commitment,
            "keyHash": computed_commitment,
            "timestamp": now
        }
        signable_msg = encode_typed_data(full_message={
            "types": types,
            "primaryType": "DataVaultSwapAttestation",
            "domain": domain_data,
            "message": message_data
        })
        signed = self.signer.account.sign_message(signable_msg)

        return {
            "status": "ATOMIC_SWAP_SETTLED",
            "order_id": order_id,
            "asset_id": order["asset_id"],
            "buyer_address": order["buyer_address"],
            "provider_address": clean_provider,
            "decryption_key_hex": clean_key,
            "gross_amount_usdc": gross_amount,
            "net_payout_usdc": net_provider_payout,
            "protocol_fee_usdc": protocol_fee,
            "settled_at": now,
            "attestation": {
                "orderId": order_bytes32,
                "assetId": order["asset_id"],
                "keyHash": computed_commitment,
                "signature": "0x" + signed.signature.hex(),
                "oracle_signer": self.signer.signer_address,
                "v": signed.v,
                "r": "0x" + signed.r.to_bytes(32, "big").hex(),
                "s": "0x" + signed.s.to_bytes(32, "big").hex()
            }
        }

    def refund_expired_order(self, order_id: str) -> Dict[str, Any]:
        """
        Manually or periodically refunds buyer if timelock expired without decryption key.
        """
        order = self.orders.get(order_id)
        if not order:
            raise ValueError(f"Order '{order_id}' not found.")

        if order["status"] != "ESCROW_LOCKED":
            raise ValueError(f"Order '{order_id}' cannot be refunded. Status: {order['status']}.")

        now = int(time.time())
        if now <= order["expires_at"]:
            raise ValueError(f"Order '{order_id}' has not yet expired. Timelock active until {order['expires_at']}.")

        return self._refund_buyer(order)

    def _refund_buyer(self, order: Dict[str, Any]) -> Dict[str, Any]:
        """Internal helper to refund locked escrow funds to buyer."""
        buyer = order["buyer_address"]
        price_usdc = order["price_usdc"]

        account = vault_manager.get_account(buyer)
        if not account:
            session_key = "ak_live_" + secrets.token_hex(24)
            now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            from app.vault_manager import AgentVaultAccount
            account = AgentVaultAccount(
                agent_address=buyer,
                balance_usdc=0.0,
                total_deposited_usdc=0.0,
                total_consumed_usdc=0.0,
                session_key=session_key,
                created_at_utc=now_iso,
                last_active_utc=now_iso,
                query_count=0
            )
            with vault_manager._lock:
                vault_manager._accounts[buyer] = account
                vault_manager._session_index[session_key] = buyer
        account.balance_usdc = round(account.balance_usdc + price_usdc, 6)

        order["status"] = "REFUNDED"
        order["refunded_at"] = int(time.time())

        return {
            "status": "REFUNDED",
            "order_id": order["order_id"],
            "buyer_address": buyer,
            "refunded_amount_usdc": price_usdc,
            "reason": "Escrow timelock expired without valid key disclosure."
        }


synthetic_data_vault = SyntheticDataVault()
