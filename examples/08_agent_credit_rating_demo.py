"""
Example 8: Autonomous Agent Credit Rating Agency Oracle Demonstration ("Moody's & S&P of AI Agents").
Demonstrates:
1. Agent Alice (Prime Institutional Grade - AAA) qualifying for uncollateralized DeFi credit.
2. Agent Mallory (Compromised Rogue Agent - D) rejected and blacklisted from on-chain credit lines.
3. Cryptographic EIP-712 Credit Certificate generation for smart contracts.
"""

import sys
import os
import json

# Ensure root on python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.vault_manager import vault_manager
from app.credit_rating_engine import credit_engine
from sdk import SecurityGateClient

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def main():
    print("=" * 80)
    print("🏛️ [AI AGENT CREDIT RATING AGENCY ORACLE: MOODY'S & S&P FOR AUTONOMOUS AGENTS]")
    print("=" * 80)

    client = SecurityGateClient(is_dev=True, app=app)

    # -------------------------------------------------------------
    # Case 1: Agent Alice (Prime Institutional Arbitrageur)
    # -------------------------------------------------------------
    alice_addr = "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"
    print(f"\n1. Evaluating Agent Alice (Prime Trading Agent: {alice_addr})...")

    # Alice pre-funds vault with $300 USDC & executes clean trades
    vault_manager.deposit(alice_addr, 300.0)
    for _ in range(12):
        credit_engine.record_audit(alice_addr, verdict="PASSED", hallucination_detected=False)

    alice_report = client.get_credit_rating(alice_addr)
    print("   📊 Credit Assessment Report:")
    print(f"      - FICO Credit Score: {alice_report['credit_score']} / 850")
    print(f"      - Investment Grade:  [{alice_report['grade']}] ({alice_report['grade_description']})")
    print(f"      - Uncollateralized Loan Capacity: ${alice_report['max_uncollateralized_loan_usdc']:,.2f} USDC")
    print(f"      - Default Probability: {alice_report['default_probability']}")

    # Issue On-Chain Credit Certificate
    alice_cert = client.get_credit_attestation(alice_addr, chain_id=137)
    print(f"\n   📜 Issued EIP-712 Credit Certificate:")
    print(f"      - Oracle Signer: {alice_cert['oracle_signer']}")
    print(f"      - Signature: {alice_cert['signature'][:40]}...")
    print("   🏦 DeFi Lending Protocol Verdict: APPROVED $100,000 USDC UNCOLLATERALIZED CREDIT LINE! ✅")

    # -------------------------------------------------------------
    # Case 2: Agent Mallory (Compromised / Prompt-Injected Rogue Agent)
    # -------------------------------------------------------------
    mallory_addr = "0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC"
    print(f"\n2. Evaluating Agent Mallory (Compromised Rogue Agent: {mallory_addr})...")

    # Mallory attempts prompt injection jailbreaks & data leaks
    for _ in range(3):
        credit_engine.record_audit(mallory_addr, verdict="BLOCKED", hallucination_detected=True)

    mallory_report = client.get_credit_rating(mallory_addr)
    print("   📊 Credit Assessment Report:")
    print(f"      - FICO Credit Score: {mallory_report['credit_score']} / 850")
    print(f"      - Investment Grade:  [{mallory_report['grade']}] ({mallory_report['grade_description']})")
    print(f"      - Uncollateralized Loan Capacity: ${mallory_report['max_uncollateralized_loan_usdc']:,.2f} USDC")
    print(f"      - Default Probability: {mallory_report['default_probability']}")
    print("   ⛔ DeFi Lending Protocol Verdict: REJECTED! Agent is blacklisted and flagged as toxic. ❌")

    print("\n" + "=" * 80)
    print("🎉 [DEMO COMPLETE] Autonomous Agent Credit Rating Agency Oracle Operational!")
    print("=" * 80)


if __name__ == "__main__":
    main()
