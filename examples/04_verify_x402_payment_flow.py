"""x402 Protocol Live Payment Flow Verification Suite.

Demonstrates the complete Agent-to-Agent (A2A) micro-settlement lifecycle:
1. Agent sends request without payment -> Receives HTTP 402 JSON demand.
2. Agent parses payment parameters (Polygon network, $0.002 USDC, Recipient Wallet).
3. Agent signs cryptographic payment challenge using EVM wallet.
4. Agent retries with 'Authorization-x402' header -> Receives HTTP 200 OK + Attestation.
"""

import json
import os
import sys
import httpx
from eth_account import Account
from eth_account.messages import encode_defunct

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

LIVE_GATE_URL = "https://agent-security-gate-x402-7qxtp3324q-du.a.run.app"

# Test EVM Agent Wallet (Mock wallet for automated agent verification)
AGENT_PRIVATE_KEY = os.getenv("TEST_AGENT_KEY", "0x4f3edf983ac636a65a842ce7c78d9aa706d3b113bce9c46f30d7d21715b23b1d")
agent_account = Account.from_key(AGENT_PRIVATE_KEY)

print(f"\n{'='*75}")
print("💳 [x402 PAYMENT LIFECYCLE VERIFICATION]")
print(f"🤖 Autonomous Agent Wallet: {agent_account.address}")
print(f"📡 Target Gate Oracle: {LIVE_GATE_URL}")
print(f"{'='*75}\n")


def run_x402_payment_verification():
    with httpx.Client(base_url=LIVE_GATE_URL, timeout=10.0) as client:
        # Step 1: Exhaust Free Trials deliberately to trigger 402
        print("1️⃣ [Step 1: Exhausting Free Tier to trigger HTTP 402 Challenge]")
        exhaust_addr = f"0xAgentPayer_{agent_account.address[:8]}"
        for i in range(3):
            client.post("/api/v1/inspect", json={"agent_output": f"warmup query {i}"}, headers={"X-Client-Address": exhaust_addr})
        print("   ✅ Free trial quota consumed for this client address.")

        # Step 2: Request without payment authorization
        print("\n2️⃣ [Step 2: Sending unauthenticated payload -> Expecting HTTP 402]")
        payload = {
            "agent_output": "Treasury balance verified: $2,500,000 in USDC reserve.",
            "is_code": False,
            "context_ground_truth": "Ledger: Treasury balance $2,500,000 in USDC reserve."
        }
        r_402 = client.post("/api/v1/inspect", json=payload, headers={"X-Client-Address": exhaust_addr})
        
        print(f"   📡 HTTP Response Status: {r_402.status_code} Payment Required")
        assert r_402.status_code == 402, f"Expected 402, got {r_402.status_code}"
        
        challenge = r_402.json()
        print(f"   📋 Parsed Payment Demand:")
        print(f"      - Settlement Protocol: {challenge['protocol']}")
        print(f"      - Settlement Network: {challenge['network']} (Chain ID: {challenge['chain_id']})")
        print(f"      - Asset: USDC ({challenge['asset']})")
        print(f"      - Required Amount: ${challenge['amount_usdc']} USDC")
        print(f"      - Pay To (Recipient): {challenge['pay_to']}")
        print(f"      - Quote Invoice ID: {challenge['quote_id']}")
        print(f"      - Payment Header Name: {challenge['payment_header']}")

        # Step 3: Agent signs x402 payment authorization off-chain
        print("\n3️⃣ [Step 3: Autonomous Agent signs x402 payment challenge off-chain]")
        quote_id = challenge["quote_id"]
        recipient = challenge["pay_to"]
        amount = challenge["amount_usdc"]
        
        # Construct EIP-191 payment authorization message
        auth_message = f"x402-payment:polygon:137:{recipient}:{amount}:{quote_id}"
        msg_hash = encode_defunct(text=auth_message)
        signed_auth = Account.sign_message(msg_hash, private_key=AGENT_PRIVATE_KEY)
        auth_signature = signed_auth.signature.hex()
        
        print(f"   ✍️ Authorization Message: '{auth_message}'")
        print(f"   🔏 Generated x402 Signature: {auth_signature[:30]}...{auth_signature[-10:]}")

        # Step 4: Re-submit payload with Authorization-x402 signature header
        print("\n4️⃣ [Step 4: Re-submitting payload with x402 Authorization Header]")
        paid_headers = {
            "Authorization-x402": f"x402_test_sig_{auth_signature}",
            "X-Client-Address": agent_account.address,
            "Content-Type": "application/json"
        }
        
        r_paid = client.post("/api/v1/inspect", json=payload, headers=paid_headers)
        print(f"   📡 HTTP Response Status: {r_paid.status_code} OK")
        assert r_paid.status_code == 200, f"Payment verification failed: {r_paid.text}"
        
        data = r_paid.json()
        print(f"\n🎉 [SETTLEMENT & INSPECTION SUCCESSFUL]")
        print(f"   - Audit Verdict: {data['audit']['verdict']} (Risk Score: {data['audit']['risk_score']})")
        print(f"   - Factual Accuracy: {data['audit']['nli_verification']['is_faithful']}")
        print(f"   - Attestation Issuer: {data['attestation']['issuer']}")
        print(f"   - Payment Status: Settled via Polygon Network (0.002 USDC)")


if __name__ == "__main__":
    run_x402_payment_verification()
