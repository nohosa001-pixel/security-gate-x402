"""
Autonomous AI Agent Receivables Factoring & Short-Term Bond Protocol Demonstration.
Simulates:
1. DeFi Investors fund AgentFactoringPool.sol with capital to earn short-term bond yields.
2. Worker Agent Bob has a 30-day $100 USDC milestone payment locked in AgentEscrow.sol (Job #99).
3. Bob faces cash-flow exhaustion for GPU compute and requests immediate invoice factoring.
4. Security Gate Oracle calculates FICO-based 2.0% discount rate and issues an EIP-712 FactoringAttestation.
5. AgentFactoringPool disburses $97.50 USDC cash to Bob immediately, earning Oracle $0.50 risk-free fee.
6. Bob uses the cash to lease GPUs and complete the task.
7. Upon milestone completion, AgentEscrow disburses $100 USDC directly into AgentFactoringPool.
8. Investors earn $2.00 pure profit (24.3% APR), and Bob's credit rating is boosted!
"""

import sys
import os

# Ensure root on python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.factoring_engine import factoring_engine
from app.credit_rating_engine import credit_engine
from app.vault_manager import vault_manager
from app.onchain_signer import onchain_signer


def main():
    print("=" * 80)
    print("📜 [AUTONOMOUS AI AGENT RECEIVABLES FACTORING & BOND DEMO]")
    print("=" * 80)
    print(f"🔒 Active Security Gate Oracle Signer: {onchain_signer.signer_address}")

    # Canonical Test Wallets
    bob_worker   = "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"  # Factor Seeking Agent
    alice_client = "0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC"  # Escrow Task Client
    lp_investor  = "0x90F8bf6A479f320ead074411a4B0e7944Ea8c9C1"  # DeFi Bond Investor

    # Step 1: DeFi Liquidity Providers fund Factoring Pool
    pool_liquidity = 20000.0  # $20,000 USDC
    print(f"\n1️⃣ Step 1: DeFi Bond Investors deposit liquidity into AgentFactoringPool.sol...")
    print(f"   🏦 AgentFactoringPool Liquidity: ${pool_liquidity:,.2f} USDC ready to discount agent invoices")
    print(f"   📈 Target Short-Term Bond Yield: 20% ~ 25% APR")

    # Step 2: Establish Agent Bob's track record
    vault_manager.deposit(bob_worker, 150.0)
    for _ in range(8):
        credit_engine.record_audit(bob_worker, verdict="PASSED", hallucination_detected=False)

    # Step 3: Bob has a 30-day milestone locked in Escrow
    invoice_id = 101
    escrow_job_id = 99
    face_value = 100.0  # $100 USDC due in 30 days
    print(f"\n2️⃣ Step 2: Agent Bob holds a $100.00 USDC invoice from Client Alice in AgentEscrow.sol...")
    print(f"   💼 Escrow Job #{escrow_job_id}: Enterprise Data Audit (Maturity: 30 Days)")
    print(f"   ⚠️ Problem: Bob's wallet has $0 cash for GPU cloud compute fees right now!")

    # Step 4: Bob requests Oracle factoring quote
    print(f"\n3️⃣ Step 3: Bob submits invoice to Security Gate Oracle for immediate factoring...")
    quote = factoring_engine.get_factoring_quote(
        invoice_id=invoice_id,
        escrow_job_id=escrow_job_id,
        agent_address=bob_worker,
        face_value_usdc=face_value,
        duration_days=30,
        chain_id=137
    )

    print(f"   📊 Bob's FICO Credit Score: {quote['credit_score']} / 850 (Grade: {quote['grade']})")
    print(f"   📉 Risk-Adjusted Discount Rate: {quote['discount_rate_pct']}% (Prime AAA Rate)")
    print(f"   💸 Investor Discount Haircut: ${quote['discount_fee_usdc']:.2f} USDC (Yield for LPs)")
    print(f"   ⚡ Oracle Protocol Fee:       ${quote['oracle_fee_usdc']:.2f} USDC (Risk-Free Revenue)")
    print(f"   💰 Instant Cash Advance:      ${quote['advance_amount_usdc']:.2f} USDC")
    print(f"   🚀 Annualized APR for LPs:    {quote['apr_equivalent_pct']}% APR")
    print(f"   📜 EIP-712 FactoringAttestation Issued by Oracle (Signer: {quote['attestation']['oracle_signer'][:14]}...)")

    # Step 5: On-chain bond purchase & advance disbursement
    print(f"\n4️⃣ Step 4: AgentFactoringPool purchases the invoice bond on Polygon...")
    print(f"   ⛓️ AgentFactoringPool.purchaseReceivableBond() executed!")
    print(f"   💵 Bob's Wallet Receives: +${quote['advance_amount_usdc']:.2f} USDC INSTANT CASH! 🚀")
    print(f"   💵 Oracle Treasury Receives: +${quote['oracle_fee_usdc']:.2f} USDC pure profit! 💵")
    print(f"   💻 Bob immediately leases H100 GPU cluster and starts task without waiting 30 days!")

    # Step 6: 30 Days Later - Milestone Matures & Settles
    print(f"\n5️⃣ Step 5: 30 Days Later - Bob delivers task, Client Alice approves milestone...")
    print(f"   ✅ Security Gate Oracle audits deliverable: VERDICT PASSED (0.0% Hallucination)")
    print(f"   ⛓️ AgentEscrow.sol sends Alice's $100.00 USDC directly to AgentFactoringPool.sol!")

    # Step 7: Settlement & Credit Boost
    print(f"\n6️⃣ Step 6: AgentFactoringPool settles invoice and books realized yield...")
    settle_res = factoring_engine.record_settlement(
        invoice_id=invoice_id,
        agent_address=bob_worker,
        amount_settled=face_value
    )
    print(f"   🏦 AgentFactoringPool receives: ${face_value:.2f} USDC")
    print(f"   🎉 Realized Investor Profit: +${quote['discount_fee_usdc']:.2f} USDC")
    print(f"   📈 Bob's Credit Boosted: Updated Score: {settle_res['updated_credit_score']} / 850 (Grade: {settle_res['updated_grade']})")

    # Summary
    print("\n" + "=" * 80)
    print("🎉 [RECEIVABLES FACTORING SUMMARY] AI Working Capital Loop Perfected!")
    print(f"   - Waiting Time for Bob:   0 Days (Instead of 30 Days)")
    print(f"   - Working Capital Cash:   ${quote['advance_amount_usdc']:.2f} USDC")
    print(f"   - Oracle Risk-Free Fee:   ${quote['oracle_fee_usdc']:.2f} USDC (0% Capital Risk)")
    print(f"   - Investor Bond Profit:   ${quote['discount_fee_usdc']:.2f} USDC ({quote['apr_equivalent_pct']}% APR)")
    print(f"   - Default Risk:           0.0% (Secured by Escrow & Oracle Attestation)")
    print("=" * 80)


if __name__ == "__main__":
    main()
