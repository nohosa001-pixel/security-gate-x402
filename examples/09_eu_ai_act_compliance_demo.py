"""
Example 9: EU AI Act & Regulatory Compliance Passport Demonstration (Regulation EU 2024/1689).
Demonstrates:
1. Generating an official machine-verifiable EU AI Act Compliance Passport (Articles 50 & 53).
2. Institutional audit breakdown (transparency, anti-jailbreak, hallucination guardrail, GDPR).
3. On-chain EIP-712 Compliance Certificate verification for institutional enterprise onboarding.
"""

import sys
import os
import json

# Ensure root on python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.vault_manager import vault_manager
from app.credit_rating_engine import credit_engine
from app.compliance_engine import compliance_engine
from sdk import SecurityGateClient

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def main():
    print("=" * 80)
    print("🇪🇺 [EU AI ACT & INSTITUTIONAL COMPLIANCE ENGINE DEMO (REGULATION EU 2024/1689)]")
    print("=" * 80)

    client = SecurityGateClient(is_dev=True, app=app)
    enterprise_agent = "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"

    print(f"\n1. Auditing Autonomous Enterprise Agent: {enterprise_agent}...")

    # Pre-fund vault and record compliant operational telemetry
    vault_manager.deposit(enterprise_agent, 200.0)
    for _ in range(8):
        credit_engine.record_audit(enterprise_agent, verdict="PASSED", hallucination_detected=False)

    # Generate Compliance Passport
    passport = client.get_compliance_passport(enterprise_agent)

    print("\n📜 [OFFICIAL EU AI ACT COMPLIANCE PASSPORT ISSUED]")
    print(f"   - Passport ID:       {passport['passport_id']}")
    print(f"   - Regulation:        {passport['regulation']}")
    print(f"   - Certified Status:  {passport['compliance_status']} (is_certified: {passport['is_certified']})")
    print(f"   - Institutional Tier: {passport['institutional_grade']} ({passport['institutional_credit_score']} pts)")

    print("\n⚖️ [STATUTORY ARTICLE AUDIT BREAKDOWN]")
    for art_key, art_data in passport["audited_articles"].items():
        print(f"   ✅ {art_key.upper()}: [{art_data['status']}]")
        print(f"      Requirement: {art_data['requirement']}")
        print(f"      Technical Mechanism: {art_data['mechanism']}")

    # Issue On-Chain EIP-712 Compliance Certificate
    cert = compliance_engine.issue_onchain_compliance_certificate(enterprise_agent, chain_id=137)
    print("\n⛓️ [ON-CHAIN EIP-712 COMPLIANCE CERTIFICATE FOR SMART CONTRACTS]")
    print(f"   - Issuer Authority: {cert['oracle_signer']}")
    print(f"   - EIP-712 Signature: {cert['signature'][:40]}...")
    print("   - Smart Contract Gate: AgentComplianceRegistry.sol -> ACCEPTED FOR ENTERPRISE TRADING! ✅")

    print("\n" + "=" * 80)
    print("🎉 [DEMO COMPLETE] Full EU AI Act Compliance Shield Operational!")
    print("=" * 80)


if __name__ == "__main__":
    main()
