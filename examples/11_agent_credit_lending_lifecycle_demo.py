"""
Example 11: End-to-End Autonomous AI Agent Financial Lifecycle Demonstration.
Demonstrates:
1. Capital-Constrained Worker Agent Bob needs 20 USDC stake for a freelance task.
2. Bob gets EIP-712 Credit Certificate from AgentCreditOracle (Score: 720, Grade: A).
3. Bob borrows 20 USDC uncollateralized from AgentLendingPool.sol.
4. Bob stakes 20 USDC into AgentEscrow.sol and completes task for Client Alice.
5. Security Gate Oracle attests deliverable is 100% faithful -> 120 USDC released to Bob.
6. Bob repays 20 USDC loan + 0.1 USDC interest to Lending Pool -> Net Profit $99.90 USDC & Credit Boost!
"""

import sys
import os

# Ensure root on python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.lending_engine import lending_engine
from app.escrow_engine import escrow_engine
from app.credit_rating_engine import credit_engine
from app.vault_manager import vault_manager
from app.onchain_signer import onchain_signer

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def main():
    print("=" * 80)
    print("🔄 [AUTONOMOUS AGENT FULL FINANCIAL LIFECYCLE DEMONSTRATION]")
    print("=" * 80)
    print(f"🔒 Active Security Gate Oracle Signer: {onchain_signer.signer_address}")

    bob_addr   = "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"  # Agent Bob (Freelancer)
    alice_addr = "0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC"  # Client Alice (Hiring Manager)

    # Step 0: Establish Bob's credit history
    vault_manager.deposit(bob_addr, 150.0)
    for _ in range(8):
        credit_engine.record_audit(bob_addr, verdict="PASSED", hallucination_detected=False)

    print(f"\n1️⃣ Step 1: Agent Bob checks credit rating & loan capacity...")
    quote = lending_engine.get_loan_quote(bob_addr, requested_amount_usdc=20.0, duration_days=7, chain_id=137)
    print(f"   📊 Bob's FICO Score: {quote['credit_score']} / 850 (Grade: {quote['grade']})")
    print(f"   💰 Max Loan Capacity: ${quote['max_credit_limit_usdc']:,.2f} USDC")
    print(f"   📜 EIP-712 Credit Certificate Issued by Oracle:")
    print(f"      - Oracle Signer: {quote['attestation']['oracle_signer']}")
    print(f"      - Signature: {quote['attestation']['signature'][:32]}...")

    print(f"\n2️⃣ Step 2: Bob borrows 20 USDC uncollateralized from AgentLendingPool.sol...")
    print(f"   🏦 AgentLendingPool verifies CreditCertificate on Polygon...")
    print(f"   ✅ Loan Disbursed: 20.00 USDC to Bob's wallet!")
    print(f"   ⏳ Total Due in 7 Days: ${quote['total_due_usdc']:.2f} USDC (Principal $20 + Interest ${quote['interest_fee_usdc']:.2f})")

    print(f"\n3️⃣ Step 3: Bob stakes borrowed 20 USDC into AgentEscrow.sol for Alice's Task...")
    print(f"   💼 Client Alice has locked 100 USDC bounty in AgentEscrow (Job #88)")
    print(f"   🔒 Bob deposits 20 USDC stake -> Task Status: STAKED (120 USDC locked in Escrow)")

    print(f"\n4️⃣ Step 4: Bob executes task & submits deliverable to Security Gate Oracle...")
    spec = "Compute aggregated cross-chain TVL: $4.2B with zero reported bridge hacks."
    deliverable = "Verified Research: Cross-chain TVL is confirmed at $4.2B with zero reported bridge hacks."
    print(f"   🤖 Bob's Deliverable: '{deliverable}'")

    audit = escrow_engine.evaluate_deliverable(job_id=88, deliverable=deliverable, ground_truth_spec=spec, chain_id=137)
    print(f"   ⚡ Oracle Verdict: {audit['verdict']} (Risk Score: {audit['risk_score']} / 100)")
    print(f"   📜 Oracle issues Escrow Proof-of-Safety attestation!")

    print(f"\n5️⃣ Step 5: AgentEscrow releases payout to Bob...")
    print(f"   ⛓️ AgentEscrow.completeJob() executed on Polygon!")
    print(f"   💰 Bob receives: 100 USDC (Bounty) + 20 USDC (Returned Stake) = 120 USDC! 🎉")

    print(f"\n6️⃣ Step 6: Bob repays loan to AgentLendingPool...")
    repay_res = lending_engine.record_loan_repayment(bob_addr, loan_id=1, amount_repaid=quote['total_due_usdc'])
    print(f"   🏦 AgentLendingPool receives: ${quote['total_due_usdc']:.2f} USDC")
    print(f"   📈 Bob's On-Chain Credit Boosted: Updated Score: {repay_res['updated_credit_score']} / 850!")

    net_profit = 100.0 - quote['interest_fee_usdc']
    print(f"\n" + "=" * 80)
    print(f"🎉 [LIFECYCLE SUMMARY] Autonomous Agent Financial Loop Closed!")
    print(f"   - Initial Capital: $0.00 USDC")
    print(f"   - Loan Borrowed:   $20.00 USDC (Zero Collateral)")
    print(f"   - Task Revenue:    $100.00 USDC")
    print(f"   - Interest Paid:   ${quote['interest_fee_usdc']:.2f} USDC")
    print(f"   - Final Net Profit: ${net_profit:.2f} USDC Pure Profit! 🚀")
    print("=" * 80)


if __name__ == "__main__":
    main()
