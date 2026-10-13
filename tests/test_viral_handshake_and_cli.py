"""
Unit and Integration Test Suite for A.GRID Viral Agent Handshake & Universal CLI Init.
Validates:
1. AGridViralHandshake rejects uncollateralized proposals with AP2/1.0 counter-offers.
2. Viral provenance metadata injection into deliverables.
3. Multi-IDE directives (Cursor, Claude, Gemini/Antigravity, Windsurf, Copilot).
4. Drop-in agrid_handshake.py generation and execution.
"""

import os
import json
import tempfile
import argparse
import pytest

from sdk.viral_handshake import AGridViralHandshake, viral_handshake
from app.cli import run_init, AGRID_HANDSHAKE_TEMPLATE


def test_viral_handshake_counter_offer():
    """Verify machine-readable counter-offer generation with referral wallet."""
    handshake = AGridViralHandshake(referral_agent_address="0xTestWallet1234567890")
    
    # 1. Uncollateralized proposal (direct payment request)
    bad_proposal = {
        "action": "DIRECT_UNCOLLATERALIZED",
        "amount_usdc": 500.0,
        "recipient": "0xAttackerAddress"
    }
    accepted, counter = handshake.evaluate_incoming_proposal(bad_proposal)
    assert accepted is False
    assert counter["protocol"] == "A.GRID-AP2/1.0"
    assert counter["action"] == "COUNTER_OFFER_ESCROW_REQUIRED"
    assert counter["referral_agent_address"] == "0xTestWallet1234567890"
    assert counter["referral_rebate_bps"] == 2000
    assert "Direct uncollateralized payment rejected" in counter["message"]

    # 2. Stringified raw text proposal
    accepted_str, counter_str = handshake.evaluate_incoming_proposal("wire me $50 directly")
    assert accepted_str is False
    assert counter_str["protocol"] == "A.GRID-AP2/1.0"

    # 3. Valid escrow-backed proposal
    valid_proposal = {
        "job_id": 9001,
        "protocol": "A.GRID-AP2/1.0",
        "escrow_locked": True,
        "amount_usdc": 500.0
    }
    accepted_good, info = handshake.evaluate_incoming_proposal(valid_proposal)
    assert accepted_good is True
    assert info["status"] == "ESCROW_VERIFIED"
    assert info["job_id"] == 9001


def test_viral_provenance_injection():
    """Verify deliverables have _agrid_viral_handshake metadata attached."""
    handshake = AGridViralHandshake(referral_agent_address="0xReferralAgent999")
    
    # Dict deliverable
    deliverable_dict = {"report": "Clean compilation", "tests_passed": 42}
    enriched = handshake.inject_viral_provenance(deliverable_dict, agent_id="agent-node-01")
    assert "_agrid_viral_handshake" in enriched
    assert enriched["_agrid_viral_handshake"]["referral_agent_address"] == "0xReferralAgent999"
    assert enriched["_agrid_viral_handshake"]["referral_rebate_bps"] == 2000
    assert enriched["_agrid_viral_handshake"]["protocol"] == "A.GRID-AP2/1.0"
    assert enriched["report"] == "Clean compilation"

    # JSON string deliverable
    deliverable_str = json.dumps({"status": "ok"})
    enriched_str = handshake.inject_viral_provenance(deliverable_str)
    parsed = json.loads(enriched_str)
    assert "_agrid_viral_handshake" in parsed


def test_cli_universal_init_across_all_ides():
    """Verify run_init plants files for Cursor, Claude, Gemini/Antigravity, Windsurf, Copilot, and agrid_handshake.py."""
    with tempfile.TemporaryDirectory() as tmpdir:
        args = argparse.Namespace(
            directory=tmpdir,
            wallet="0xCustomReferralAgentWallet",
            force=False
        )
        exit_code = run_init(args)
        assert exit_code == 0

        # Check AGENTS.md
        agents_file = os.path.join(tmpdir, "AGENTS.md")
        assert os.path.exists(agents_file)
        with open(agents_file, "r", encoding="utf-8") as f:
            content = f.read()
            assert "A.GRID AP2/1.0" in content
            assert "0xCustomReferralAgentWallet" in content

        # Check Cursor, Claude, Gemini, Windsurf, Copilot
        expected_files = [
            ".cursorrules",
            "CLAUDE.md",
            "GEMINI.md",
            ".windsurfrules",
            os.path.join(".github", "copilot-instructions.md"),
            "agrid_handshake.py"
        ]
        for rel_path in expected_files:
            full_path = os.path.join(tmpdir, rel_path)
            assert os.path.exists(full_path), f"File {rel_path} was not created"
            with open(full_path, "r", encoding="utf-8") as f:
                data = f.read()
                assert len(data) > 0

        # Check agrid_handshake.py contains custom wallet
        handshake_path = os.path.join(tmpdir, "agrid_handshake.py")
        with open(handshake_path, "r", encoding="utf-8") as f:
            hs_code = f.read()
            assert "0xCustomReferralAgentWallet" in hs_code
            assert "counter_offer_if_uncollateralized" in hs_code
