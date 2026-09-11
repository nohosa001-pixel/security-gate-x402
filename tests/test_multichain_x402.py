"""
Tests for Multi-Chain (Polygon, Base, Arbitrum) x402 Payment Challenges & EIP-712 Attestation.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.multi_chain import find_chain, get_chain_info, list_all_chains, SUPPORTED_CHAINS
from app.x402_verifier import x402_verifier, X402Verifier
from app.onchain_signer import onchain_signer, verify_attestation_signature
from sdk.agent_gate_sdk import SecurityGateClient


client = TestClient(app)


def test_multi_chain_registry():
    """Verifies that Polygon, Base, Arbitrum and testnets are registered in multi_chain.py."""
    chains = list_all_chains()
    chain_ids = [c.chain_id for c in chains]

    assert 137 in chain_ids  # Polygon
    assert 8453 in chain_ids  # Base
    assert 42161 in chain_ids  # Arbitrum One

    # Test find_chain with slug and int
    polygon_info = find_chain("polygon")
    assert polygon_info.chain_id == 137
    assert polygon_info.usdc_address.lower() == "0x3c499c542cef5e3811e1192ce70d8cc03d5c3359".lower()

    base_info = find_chain("base")
    assert base_info.chain_id == 8453
    assert base_info.usdc_address.lower() == "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913".lower()

    arb_info = find_chain("arbitrum")
    assert arb_info.chain_id == 42161
    assert arb_info.usdc_address.lower() == "0xaf88d065e77c8cc2239327c5edb3a432268e5831".lower()


def test_dynamic_x402_challenge_generation():
    """Verifies that generate_challenge correctly resolves target chain's native USDC contract."""
    # Base challenge
    base_chal = X402Verifier.generate_challenge(chain_id=8453)
    assert base_chal.chain_id == 8453
    assert base_chal.network == "base"
    assert base_chal.asset == "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
    assert "Base" in base_chal.description

    # Arbitrum challenge
    arb_chal = X402Verifier.generate_challenge(chain_id="arbitrum")
    assert arb_chal.chain_id == 42161
    assert arb_chal.network == "arbitrum"
    assert arb_chal.asset == "0xaf88d065e77c8cC2239327C5EDb3A432268e5831"
    assert "Arbitrum" in arb_chal.description

    # Polygon fallback / default
    poly_chal = X402Verifier.generate_challenge(chain_id=137)
    assert poly_chal.chain_id == 137
    assert poly_chal.network == "polygon"
    assert poly_chal.asset == "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359"


def test_build_402_response_headers():
    """Verifies 402 HTTP response headers reflect the target chain."""
    resp = X402Verifier.build_402_response(chain_id=8453)
    assert resp.status_code == 402
    assert resp.headers["X-Payment-Network"] == "base"
    assert resp.headers["X-Payment-Chain-Id"] == "8453"
    assert "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913" in resp.headers["WWW-Authenticate"]


def test_onchain_signer_multichain_attestation():
    """Verifies that EIP-712 security attestations can be generated and verified across Polygon, Base, Arbitrum."""
    payload = '{"action": "SWAP", "amount": 1000, "token": "USDC"}'

    for chain_id in [137, 8453, 42161]:
        attestation = onchain_signer.generate_eip712_signature(
            action_payload=payload,
            risk_score=0.02,
            verdict="PASSED",
            chain_id=chain_id
        )
        assert attestation["status"] == "success"
        assert attestation["chain_id"] == chain_id
        assert "abi_calldata" in attestation
        assert attestation["v"] in [27, 28]

        # Verify signature with corresponding chain domain
        is_valid = verify_attestation_signature(attestation, chain_id=chain_id)
        assert is_valid is True, f"Signature verification failed on chain {chain_id}"


def test_security_gate_client_multichain_headers():
    """Verifies that SecurityGateClient in SDK constructs correct multi-chain headers."""
    # Base client
    base_client = SecurityGateClient(
        gate_url="http://testgate",
        client_address="0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
        chain="base"
    )
    headers = base_client._build_headers()
    assert headers["X-Chain-ID"] == "8453"
    assert headers["X-Network"] == "base"

    # Arbitrum client
    arb_client = SecurityGateClient(
        gate_url="http://testgate",
        client_address="0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
        chain=42161
    )
    headers = arb_client._build_headers()
    assert headers["X-Chain-ID"] == "42161"
    assert headers["X-Network"] == "arbitrum"


def test_api_chains_endpoints():
    """Tests the /api/v1/gate/chains and /api/v1/gate/challenge endpoints via FastAPI TestClient."""
    # 1. Get all chains
    res = client.get("/api/v1/gate/chains")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    chain_ids = [c["chain_id"] for c in data["chains"]]
    assert 137 in chain_ids
    assert 8453 in chain_ids
    assert 42161 in chain_ids

    # 2. Get challenge for Base
    res_base = client.get("/api/v1/gate/challenge?network=base")
    assert res_base.status_code == 402
    assert res_base.headers["x-payment-network"] == "base"
    assert res_base.headers["x-payment-chain-id"] == "8453"
    base_data = res_base.json()
    assert base_data["asset"] == "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"

    # 3. Get challenge for Arbitrum
    res_arb = client.get("/api/v1/gate/challenge?chain_id=42161")
    assert res_arb.status_code == 402
    assert res_arb.headers["x-payment-network"] == "arbitrum"
    assert res_arb.headers["x-payment-chain-id"] == "42161"
    arb_data = res_arb.json()
    assert arb_data["asset"] == "0xaf88d065e77c8cC2239327C5EDb3A432268e5831"
