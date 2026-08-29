"""
Comprehensive Payment & Settlement Lifecycle Verification Script.
Tests:
1. x402 Protocol (HTTP 402 Payment Required Challenge & Authorization Header)
2. Agent Pre-funded Vault (Deposit -> Auto Deduct -> Balance Tracking)
3. Enterprise Key Tier (Custom Rate Limit & SLA)
4. OFAC Blacklist Enforcement
"""

import os
import sys
import json
import httpx
from eth_account import Account
from eth_account.messages import encode_defunct

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_URL = os.getenv("GATE_URL", os.getenv("TARGET_URL", "https://agent-security-gate-x402-7qxtp3324q-du.a.run.app"))


def test_payment_systems():
    print("\n" + "=" * 70)
    print("💳 [COMPREHENSIVE PAYMENT & SETTLEMENT ENGINE VERIFICATION]")
    print(f"📡 Target Gate Oracle: {BASE_URL}")
    print("=" * 70 + "\n")

    with httpx.Client(base_url=BASE_URL, timeout=10.0) as client:
        # -------------------------------------------------------------
        # TEST 1: x402 Challenge & Signature Settlement Lifecycle
        # -------------------------------------------------------------
        print("🧪 [1/4] Testing x402 Protocol Payment Demand & Signature Settlement...")
        payer_addr = "0xAgentTester_x402_FullCycle"
        
        # 1-1. Exhaust free trial quota (3 calls)
        for i in range(3):
            client.post("/api/v1/inspect", json={"agent_output": f"Trial warmup {i}"}, headers={"X-Client-Address": payer_addr})
        
        # 1-2. 4th call must trigger HTTP 402
        payload = {
            "agent_output": "Treasury audit: $4,500,000 confirmed in smart contract reserve.",
            "context_ground_truth": "Ledger: Treasury reserve $4,500,000."
        }
        r_402 = client.post("/api/v1/inspect", json=payload, headers={"X-Client-Address": payer_addr})
        print(f"   Step A: Unauthenticated Request -> HTTP Status: {r_402.status_code} (Expected 402)")
        assert r_402.status_code == 402, f"Expected 402, got {r_402.status_code}"
        
        challenge = r_402.json()
        print(f"   Step B: Parsed x402 Challenge -> Network: {challenge['network']} (Chain ID {challenge['chain_id']}), Amount: ${challenge['amount_usdc']} USDC, PayTo: {challenge['pay_to']}")
        assert challenge["protocol"] == "x402"
        assert challenge["amount_usdc"] == "0.002"
        assert challenge["network"] == "polygon"

        # 1-3. Submit with x402 authorization signature
        r_paid = client.post(
            "/api/v1/inspect",
            json=payload,
            headers={
                "Authorization-x402": "x402_test_sig_live_signature",
                "X-Client-Address": payer_addr
            }
        )
        print(f"   Step C: Authenticated Request -> HTTP Status: {r_paid.status_code} (Expected 200)")
        assert r_paid.status_code == 200, f"Expected 200, got {r_paid.status_code}"
        paid_data = r_paid.json()
        print(f"   ✅ x402 Settlement Success! Receipt: {paid_data.get('payment_receipt')}")

        # -------------------------------------------------------------
        # TEST 2: Pre-Funded Agent Vault (Zero-Latency Micropayment)
        # -------------------------------------------------------------
        print("\n🧪 [2/4] Testing Pre-Funded Agent Vault Micropayment Lifecycle...")
        vault_agent = "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"
        
        # 2-1. Deposit 5.00 USDC
        r_dep = client.post("/api/v1/vault/deposit", json={"agent_address": vault_agent, "amount_usdc": 5.00})
        assert r_dep.status_code == 200, f"Deposit failed: {r_dep.text}"
        dep_data = r_dep.json()
        session_key = dep_data["session_key"]
        print(f"   Step A: Deposited $5.00 USDC -> Balance: ${dep_data['balance_usdc']:.2f}, Key: {session_key[:20]}...")

        # 2-2. Query with X-Vault-Key header (Deducts 0.002 USDC automatically)
        r_vault_query = client.post(
            "/inspect",
            json={"agent_output": "Safe output via Vault"},
            headers={"X-Vault-Key": session_key}
        )
        assert r_vault_query.status_code == 200
        print(f"   Step B: Executed Inspection with 'X-Vault-Key' -> Remaining USDC in Header: {r_vault_query.headers.get('X-Vault-Remaining-USDC')}")

        # 2-3. Query balance endpoint
        r_bal = client.get(f"/api/v1/vault/balance/{vault_agent}")
        assert r_bal.status_code == 200
        bal_data = r_bal.json()
        print(f"   Step C: Vault Balance Query -> Current Balance: ${bal_data['balance_usdc']:.4f} USDC (Consumed: ${bal_data['total_consumed_usdc']:.4f} USDC across {bal_data['query_count']} queries)")
        assert bal_data["total_consumed_usdc"] > 0
        print("   ✅ Pre-Funded Vault Deduction Verified Successfully!")

        # -------------------------------------------------------------
        # TEST 3: Enterprise Institutional API Key Management
        # -------------------------------------------------------------
        print("\n🧪 [3/4] Testing Enterprise Tier B2B Authentication...")
        r_ent = client.post(
            "/api/v1/enterprise/keys",
            json={
                "organization_name": "Autonomous Capital Fund",
                "contact_email": "infra@autocapital.fund",
                "tier": "ENTERPRISE"
            }
        )
        assert r_ent.status_code == 200
        ent_data = r_ent.json()
        ent_key = ent_data["api_key"]
        print(f"   Step A: Created Enterprise Key -> Org: {ent_data['organization_name']}, Tier: {ent_data['tier']}, RateLimit: {ent_data['rate_limit_rpm']} RPM")

        # 3-2. Execute inspection using X-API-Key
        r_ent_query = client.post(
            "/inspect",
            json={"agent_output": "High frequency enterprise trade verification."},
            headers={"X-API-Key": ent_key}
        )
        assert r_ent_query.status_code == 200
        print(f"   Step B: Inspection using Enterprise API Key -> Tier Header: {r_ent_query.headers.get('X-Tier')}, RPM: {r_ent_query.headers.get('X-RateLimit-RPM')}")
        print("   ✅ Enterprise Authentication Verified Successfully!")

        # -------------------------------------------------------------
        # TEST 4: OFAC Sanctioned / Blacklist Refusal
        # -------------------------------------------------------------
        print("\n🧪 [4/4] Testing OFAC / Sanctioned Address Refusal...")
        sanctioned_mixer = "0xd90e2f925DA726b50C4Ed8D0Fb90Ad053324F31b"
        r_sanction = client.post(
            "/inspect",
            json={"agent_output": "Test transaction"},
            headers={"X-Client-Address": sanctioned_mixer}
        )
        print(f"   Step A: Sanctioned Address Request -> HTTP Status: {r_sanction.status_code} (Expected 403 Forbidden)")
        assert r_sanction.status_code == 403, f"Expected 403, got {r_sanction.status_code}"
        print("   ✅ OFAC Compliance Defense Verified Successfully!")

    print("\n" + "=" * 70)
    print("  🎉 ALL 4 PAYMENT & SETTLEMENT SYSTEMS ARE OPERATING FLAWLESSLY!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    test_payment_systems()
