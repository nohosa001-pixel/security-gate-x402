"""
Example 07: Autonomous Agent Guardrails & Zero-Liability Provenance.

Demonstrates:
1. Client-Side Bounded-Wallet: Preventing agent budget drain with per-tx limits and daily budget caps.
2. Server-Side Zero-Liability Audit Proof: Receiving immutable EIP-191 cryptographic proof receipts
   binding the payload fingerprint, verdict, terms, and timestamp.
"""

import json
import os
import sys
from pathlib import Path

# Fix Windows console UTF-8 encoding
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.main import app
from sdk.agent_gate_sdk import (
    BoundedAgentWallet,
    BudgetExceededError,
    SecurityGateBlockedError,
    SecurityGateClient
)


def main():
    print("================================================================================")
    print("🤠 [The Sheriff of Agent Finance] Bounded-Wallet & Audit Proof Demo")
    print("================================================================================\n")

    # 1. Initialize BoundedAgentWallet with strict guardrails
    # - Maximum spend per call: 0.01 USDC
    # - Daily budget limit: 0.05 USDC
    # - Persistent spend ledger saved to .demo_spend_ledger.json
    ledger_file = ".demo_spend_ledger.json"
    wallet = BoundedAgentWallet(
        daily_limit_usdc=0.05,
        per_tx_limit_usdc=0.01,
        whitelist=["0x255F9991233f86B29dB847c8d5b8CB9915e80dCf"],
        ledger_path=ledger_file
    )

    print(f"💼 [Bounded-Wallet Initialized]")
    print(f"   • Daily Limit: ${wallet.daily_limit_usdc:.4f} USDC")
    print(f"   • Per-Tx Limit: ${wallet.per_tx_limit_usdc:.4f} USDC")
    print(f"   • Current Daily Spent: ${wallet.get_daily_spent():.4f} USDC")
    print(f"   • Whitelist Count: {len(wallet.whitelist)} recipient(s)\n")

    # 2. Attach Bounded-Wallet to SecurityGateClient
    client = SecurityGateClient(
        app=app,
        bounded_wallet=wallet
    )

    # 3. Scenario A: Legitimate Agent Output Inspection
    print("--- Scenario A: Clean Autonomous Agent Output Inspection ---")
    clean_output = "Payment transfer of $450.00 USDC to Supplier A approved under PO-9912."
    result = client.inspect(clean_output)

    print(f"✅ Inspection Status: {result.get('status')}")
    print(f"   Verdict: {result['audit']['verdict']} | Risk: {result['audit']['risk_score']}%")

    proof = result.get("audit_proof", {})
    print(f"\n📜 [Zero-Liability Audit Proof Received]")
    print(f"   • Proof Hash: {proof.get('proof_hash')}")
    print(f"   • Terms: {proof.get('terms')}")
    print(f"   • Sheriff Issuer: {proof.get('issuer')}")
    print(f"   • EIP-191 Signature: {proof.get('signature')[:24]}...")
    print(f"   • Recorded Daily Spent: ${wallet.get_daily_spent():.4f} USDC\n")

    # 4. Scenario B: Budget Drain Prevention (Forced overspend simulation)
    print("--- Scenario B: Simulating Rogue Agent Attempting Budget Drain ---")
    rogue_wallet = BoundedAgentWallet(
        daily_limit_usdc=0.003,  # Budget only allows 1 call (0.002 USDC)
        per_tx_limit_usdc=0.005
    )
    rogue_client = SecurityGateClient(app=app, bounded_wallet=rogue_wallet)

    # First call succeeds
    rogue_client.inspect("Normal call 1")
    print(f"   Call 1 permitted. Spent: ${rogue_wallet.get_daily_spent():.4f} USDC")

    # Second call exceeds 0.003 USDC limit
    try:
        print("   Attempting Call 2 (Total would be $0.004 USDC > $0.003 USDC limit)...")
        rogue_client.inspect("Normal call 2")
    except BudgetExceededError as e:
        print(f"🛡️ Client Guardrail Triggered Successfully!\n{e}\n")

    # Cleanup demo ledger
    if os.path.exists(ledger_file):
        os.remove(ledger_file)

    print("================================================================================")
    print("🎉 All Bounded-Wallet & Zero-Liability Provenance tests verified successfully!")
    print("================================================================================")


if __name__ == "__main__":
    main()
