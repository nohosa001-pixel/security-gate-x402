"""
Tests for Phase 2: Synthetic Data Vault (ZK Decryption Atomic Swap) & Micro-Licensing Engine.
Validates zero-trust data exchange, key commitment verification, timelock refunds,
and per-query / per-weight streaming capability quotas.
"""

import time
import secrets
import eth_utils
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.synthetic_data_vault import synthetic_data_vault
from app.micro_licensing_engine import micro_licensing_engine
from app.vault_manager import vault_manager
from app.credit_rating_engine import credit_engine
from sdk.agent_gate_sdk import UniversalEscrowClient


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_registries():
    """Clear in-memory state before each test run to ensure strict hermetic isolation."""
    synthetic_data_vault.assets.clear()
    synthetic_data_vault.orders.clear()
    micro_licensing_engine.tariffs.clear()
    micro_licensing_engine.tokens.clear()
    with vault_manager._lock:
        vault_manager._accounts.clear()
        vault_manager._session_index.clear()


class TestSyntheticDataVault:
    def test_register_and_atomic_swap_success(self, client):
        """Seller registers encrypted CleanWeb data, buyer locks escrow, and seller unlocks via valid key."""
        seller = "0x2a01000000000000000000000000000000000001"
        buyer = "0x2a02000000000000000000000000000000000002"

        # Pre-fund buyer vault with 500 USDC
        vault_manager.deposit(buyer, 500.0)

        # 1. Generate key and commitment
        raw_key = "0x" + secrets.token_hex(32)
        raw_key_bytes = eth_utils.to_bytes(hexstr=raw_key)
        key_commitment = "0x" + eth_utils.keccak(raw_key_bytes).hex()
        cipher_hash = "0x" + secrets.token_hex(32)

        # Register CleanWeb Asset
        reg_res = client.post("/api/v1/vault/data/register", json={
            "asset_id": "CLEANWEB-GRID-DATA-01",
            "provider_address": seller,
            "asset_type": "CLEANWEB_DATASET",
            "ciphertext_hash": cipher_hash,
            "key_commitment": key_commitment,
            "price_usdc": 100.0,
            "zk_proof": "0x" + "a" * 64,
            "metadata": {"grid_zone": "DE-LU", "resolution_min": 15}
        })
        assert reg_res.status_code == 200, reg_res.text
        assert reg_res.json()["status"] == "REGISTERED"

        # 2. Buyer locks atomic swap escrow
        lock_res = client.post("/api/v1/vault/data/swap/lock", json={
            "order_id": "SWAP-ORD-1001",
            "asset_id": "CLEANWEB-GRID-DATA-01",
            "buyer_address": buyer,
            "chain_id": 137,
            "timelock_seconds": 3600
        })
        assert lock_res.status_code == 200, lock_res.text
        assert lock_res.json()["status"] == "ESCROW_LOCKED"
        assert lock_res.json()["locked_amount_usdc"] == 100.0

        # Buyer balance should now be 400 USDC (500 - 100)
        assert vault_manager.get_account(buyer).balance_usdc == 400.0

        # 3. Seller reveals decryption key matching commitment
        decrypt_res = client.post("/api/v1/vault/data/swap/decrypt", json={
            "order_id": "SWAP-ORD-1001",
            "provider_address": seller,
            "decryption_key_hex": raw_key,
            "chain_id": 137
        })
        assert decrypt_res.status_code == 200, decrypt_res.text
        data = decrypt_res.json()
        assert data["status"] == "ATOMIC_SWAP_SETTLED"
        assert data["decryption_key_hex"] == raw_key
        assert data["gross_amount_usdc"] == 100.0
        assert data["protocol_fee_usdc"] == 0.25  # 0.25% fee
        assert data["net_payout_usdc"] == 99.75
        assert "attestation" in data
        assert data["attestation"]["signature"].startswith("0x")

        # Seller balance should be credited 99.75 USDC
        assert vault_manager.get_account(seller).balance_usdc == 99.75

    def test_atomic_swap_rejects_fraudulent_key(self, client):
        """Seller attempts to reveal a fraudulent key that doesn't match commitment; fails & penalized."""
        seller = "0x2a03000000000000000000000000000000000003"
        buyer = "0x2a04000000000000000000000000000000000004"
        vault_manager.deposit(buyer, 300.0)

        real_key = "0x" + secrets.token_hex(32)
        real_key_bytes = eth_utils.to_bytes(hexstr=real_key)
        key_commitment = "0x" + eth_utils.keccak(real_key_bytes).hex()

        client.post("/api/v1/vault/data/register", json={
            "asset_id": "BIO-PROTEIN-TARGET-02",
            "provider_address": seller,
            "asset_type": "BIOPHARMA_MOLECULAR",
            "ciphertext_hash": "0x" + secrets.token_hex(32),
            "key_commitment": key_commitment,
            "price_usdc": 150.0
        })

        client.post("/api/v1/vault/data/swap/lock", json={
            "order_id": "SWAP-ORD-FRAUD",
            "asset_id": "BIO-PROTEIN-TARGET-02",
            "buyer_address": buyer,
            "chain_id": 137
        })

        # Submit fake key
        fake_key = "0x" + secrets.token_hex(32)
        dec_res = client.post("/api/v1/vault/data/swap/decrypt", json={
            "order_id": "SWAP-ORD-FRAUD",
            "provider_address": seller,
            "decryption_key_hex": fake_key,
            "chain_id": 137
        })
        assert dec_res.status_code == 400
        assert "Commitment mismatch" in dec_res.json()["detail"]

    def test_atomic_swap_timelock_expiry_refund(self, client):
        """If timelock expires without seller key reveal, buyer is refunded in full."""
        seller = "0x2a05000000000000000000000000000000000005"
        buyer = "0x2a06000000000000000000000000000000000006"
        vault_manager.deposit(buyer, 200.0)

        client.post("/api/v1/vault/data/register", json={
            "asset_id": "AI-LORA-FINETUNE-03",
            "provider_address": seller,
            "asset_type": "AI_WEIGHT_LORA",
            "ciphertext_hash": "0x" + secrets.token_hex(32),
            "key_commitment": "0x" + secrets.token_hex(32),
            "price_usdc": 120.0
        })

        # Lock with short timelock (60 sec)
        client.post("/api/v1/vault/data/swap/lock", json={
            "order_id": "SWAP-ORD-EXPIRE",
            "asset_id": "AI-LORA-FINETUNE-03",
            "buyer_address": buyer,
            "timelock_seconds": 60
        })
        assert vault_manager.get_account(buyer).balance_usdc == 80.0

        # Simulate time passage beyond 60s
        synthetic_data_vault.orders["SWAP-ORD-EXPIRE"]["expires_at"] = int(time.time()) - 10

        ref_res = client.post("/api/v1/vault/data/swap/refund/SWAP-ORD-EXPIRE")
        assert ref_res.status_code == 200, ref_res.text
        assert ref_res.json()["status"] == "REFUNDED"
        assert ref_res.json()["refunded_amount_usdc"] == 120.0

        # Buyer balance restored to 200 USDC
        assert vault_manager.get_account(buyer).balance_usdc == 200.0


class TestMicroLicensingEngine:
    def test_register_tariff_and_purchase_quota(self, client):
        """Provider registers $0.001/query tariff; consumer buys 5000 queries with vault debit."""
        provider = "0x2b01000000000000000000000000000000000001"
        consumer = "0x2b02000000000000000000000000000000000002"
        vault_manager.deposit(consumer, 50.0)

        # 1. Register Tariff
        tar_res = client.post("/api/v1/license/tariff/register", json={
            "asset_id": "API-SMILES-CONVERTER",
            "provider_address": provider,
            "rate_type": "PER_QUERY",
            "price_per_unit_usdc": 0.001,
            "min_units": 10,
            "max_units_per_order": 50000
        })
        assert tar_res.status_code == 200, tar_res.text
        assert tar_res.json()["status"] == "TARIFF_REGISTERED"

        # 2. Purchase Quota (5000 queries * $0.001 = $5.00 USDC)
        buy_res = client.post("/api/v1/license/quota/purchase", json={
            "asset_id": "API-SMILES-CONVERTER",
            "consumer_address": consumer,
            "units_requested": 5000,
            "chain_id": 137
        })
        assert buy_res.status_code == 200, buy_res.text
        data = buy_res.json()
        assert data["status"] == "ISSUED"
        assert data["total_paid_usdc"] == 5.0
        assert data["units_authorized"] == 5000
        assert data["capability_token"].startswith("bearer_MLT-")
        token_id = data["token_id"]

        # Check balances: consumer debited 5.0, provider credited (5.0 - 0.25% = 4.9875)
        assert vault_manager.get_account(consumer).balance_usdc == 45.0
        assert vault_manager.get_account(provider).balance_usdc == 4.9875

        # 3. Meter Usage (Consume 50 queries)
        meter_res = client.post("/api/v1/license/usage/meter", json={
            "token_id": token_id,
            "units_consumed": 50
        })
        assert meter_res.status_code == 200, meter_res.text
        m_data = meter_res.json()
        assert m_data["status"] == "METERED"
        assert m_data["units_consumed_this_call"] == 50
        assert m_data["units_remaining"] == 4950
        assert m_data["is_exhausted"] is False

    def test_meter_usage_quota_exhaustion_and_overuse_block(self, client):
        """Metering beyond authorized units fails with 400."""
        provider = "0x2b03000000000000000000000000000000000003"
        consumer = "0x2b04000000000000000000000000000000000004"
        vault_manager.deposit(consumer, 50.0)

        client.post("/api/v1/license/tariff/register", json={
            "asset_id": "AI-LORA-SHARD-STREAM",
            "provider_address": provider,
            "rate_type": "PER_WEIGHT_MB",
            "price_per_unit_usdc": 0.05,
            "min_units": 1
        })

        buy_res = client.post("/api/v1/license/quota/purchase", json={
            "asset_id": "AI-LORA-SHARD-STREAM",
            "consumer_address": consumer,
            "units_requested": 10
        })
        token_id = buy_res.json()["token_id"]

        # Over-consume 15 MB (only 10 authorized)
        meter_res = client.post("/api/v1/license/usage/meter", json={
            "token_id": token_id,
            "units_consumed": 15
        })
        assert meter_res.status_code == 400
        assert "Quota exceeded" in meter_res.json()["detail"]


class TestPhase2SDKIntegration:
    def test_sdk_full_phase2_flow(self):
        """UniversalEscrowClient executes full Data Vault and Micro-Licensing workflow."""
        sdk = UniversalEscrowClient(chain_id=137, app=app)
        provider = "0x2c01000000000000000000000000000000000001"
        consumer = "0x2c02000000000000000000000000000000000002"
        vault_manager.deposit(consumer, 500.0)

        # 1. SDK Register Data Asset
        raw_key = "0x" + secrets.token_hex(32)
        key_commitment = "0x" + eth_utils.keccak(eth_utils.to_bytes(hexstr=raw_key)).hex()

        reg = sdk.register_data_asset(
            asset_id="SDK-DATA-01",
            provider_address=provider,
            asset_type="SYNTHETIC_CLINICAL",
            ciphertext_hash="0x" + secrets.token_hex(32),
            key_commitment=key_commitment,
            price_usdc=200.0
        )
        assert reg["status"] == "REGISTERED"

        # 2. SDK Create Swap Order
        lock = sdk.create_data_swap_order(
            order_id="SDK-ORDER-01",
            asset_id="SDK-DATA-01",
            buyer_address=consumer,
            timelock_seconds=3600
        )
        assert lock["status"] == "ESCROW_LOCKED"

        # 3. SDK Execute Swap Decrypt
        dec = sdk.execute_data_swap_decrypt(
            order_id="SDK-ORDER-01",
            provider_address=provider,
            decryption_key_hex=raw_key
        )
        assert dec["status"] == "ATOMIC_SWAP_SETTLED"
        assert dec["decryption_key_hex"] == raw_key

        # 4. SDK Micro-Licensing Tariff Register & Purchase
        sdk.register_licensing_tariff(
            asset_id="SDK-API-01",
            provider_address=provider,
            rate_type="PER_INFERENCE_STEP",
            price_per_unit_usdc=0.0002
        )

        quota = sdk.purchase_license_quota(
            asset_id="SDK-API-01",
            consumer_address=consumer,
            units_requested=10000
        )
        assert quota["status"] == "ISSUED"
        token_id = quota["token_id"]

        # 5. SDK Meter Usage
        meter = sdk.meter_license_usage(token_id=token_id, units_consumed=500)
        assert meter["status"] == "METERED"
        assert meter["units_remaining"] == 9500
