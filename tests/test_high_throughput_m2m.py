"""
High-Throughput M2M Agent Traffic & Uncapped Pre-payment Verification Test Suite.
Verifies unlimited pre-payment deposits, rate limit bypass for authenticated agents,
batch inspection endpoint, and vault state persistence.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.vault_manager import vault_manager, VaultManager
from app.schemas import PricingTier


@pytest.fixture
def client():
    return TestClient(app)


def test_uncapped_deposit_limits(client):
    """Verifies deposit enforces minimum $50.00 USDC while having no upper ceiling."""
    import uuid
    addr1 = f"0x{uuid.uuid4().hex[:40]}"
    addr2 = f"0x{uuid.uuid4().hex[:40]}"
    addr3 = f"0x{uuid.uuid4().hex[:40]}"

    # 1. Below minimum ($10.00 USDC) should be rejected (422 validation error)
    r_sub = client.post("/api/v1/vault/deposit", json={
        "agent_address": addr1,
        "amount_usdc": 10.0
    })
    assert r_sub.status_code == 422

    # 2. Standard minimum deposit ($50.00 USDC)
    r1 = client.post("/api/v1/vault/deposit", json={
        "agent_address": addr2,
        "amount_usdc": 50.0
    })
    assert r1.status_code == 200
    data1 = r1.json()
    assert data1["status"] == "success"
    assert data1["balance_usdc"] == 50.0

    # 3. Large institutional deposit ($1,000,000.00 USDC)
    r2 = client.post("/api/v1/vault/deposit", json={
        "agent_address": addr3,
        "amount_usdc": 1000000.0
    })
    assert r2.status_code == 200
    data2 = r2.json()
    assert data2["balance_usdc"] == 1000000.0


def test_high_throughput_burst_without_rate_limit(client):
    """
    Verifies that an autonomous agent using X-Vault-Key can execute
    hundreds of queries consecutively without getting blocked by 120 RPM IP rate limiting.
    """
    # Deposit funds to get session key
    dep_resp = client.post("/api/v1/vault/deposit", json={
        "agent_address": "0x3333333333333333333333333333333333333333",
        "amount_usdc": 100.0
    })
    assert dep_resp.status_code == 200
    vault_key = dep_resp.json()["session_key"]

    # Execute 150 consecutive requests (exceeds default 120 RPM IP rate limit)
    payload = {
        "agent_output": "Agent executed safe deterministic operation.",
        "is_code": False
    }
    headers = {"X-Vault-Key": vault_key}

    success_count = 0
    for i in range(150):
        resp = client.post("/api/v1/inspect", json=payload, headers=headers)
        if resp.status_code == 200:
            success_count += 1

    assert success_count == 150, f"Expected all 150 requests to succeed, got {success_count}"


def test_batch_inspection_endpoint(client):
    """Verifies high-throughput batch inspection for multi-output agent pipelines."""
    dep_resp = client.post("/api/v1/vault/deposit", json={
        "agent_address": "0x4444444444444444444444444444444444444444",
        "amount_usdc": 50.0
    })
    vault_key = dep_resp.json()["session_key"]

    batch_payload = {
        "items": [
            {"agent_output": "Safe clean calculation result: 42", "is_code": False},
            {"agent_output": "import os; os.system('cat /etc/passwd')", "is_code": True},
            {"agent_output": "Quarterly net profit was $500K.", "is_code": False, "context_ground_truth": "Q3 profit: $500K"}
        ]
    }

    resp = client.post("/api/v1/inspect/batch", json=batch_payload, headers={"X-Vault-Key": vault_key})
    assert resp.status_code == 200
    data = resp.json()

    assert data["status"] == "success"
    assert data["total_count"] == 3
    assert data["passed_count"] == 2
    assert data["blocked_count"] == 1  # Malicious os.system code blocked
    assert len(data["results"]) == 3


def test_vault_persistence(tmp_path):
    """Verifies that vault state persists to disk and can be reloaded."""
    state_file = tmp_path / "vault_state.json"
    vm1 = VaultManager(state_file_path=str(state_file))
    
    # Deposit into vm1
    acc = vm1.deposit("0x5555555555555555555555555555555555555555", 75.50)
    assert acc.balance_usdc == 75.50
    session_key = acc.session_key

    # Initialize a new vm2 pointing to same state file
    vm2 = VaultManager(state_file_path=str(state_file))
    reloaded_acc = vm2.get_account(session_key)
    assert reloaded_acc is not None
    assert reloaded_acc.balance_usdc == 75.50
