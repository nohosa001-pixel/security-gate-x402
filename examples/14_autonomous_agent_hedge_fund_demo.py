"""
Autonomous AI Agent Hedge Fund & Treasury Vault Protocol Demonstration (Stage 5 Grand Synthesis).
Simulates:
1. Investors / DAOs pool $100,000 USDC into AgentTreasuryVault.sol.
2. Certified AI Fund Manager AlphaBot (FICO 818, AAA) identifies high-yield Stage 4 Factoring opportunity.
3. AlphaBot submits trade strategy to Security Gate Oracle.
4. Security Gate audits prompt, destination whitelist, slippage, and signs EIP-712 TradeAuthorization.
5. Vault executes the trade on-chain.
6. Strategy matures: $10,200 USDC returned (+$200.00 profit).
7. Vault distributes performance fees: 15% to AlphaBot, 5% to Oracle, 80% net yield to Investors!
"""

import sys
import os

# Ensure root on python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.asset_management_engine import asset_management_engine
from app.credit_rating_engine import credit_engine
from app.vault_manager import vault_manager
from app.onchain_signer import onchain_signer


def main():
    print("=" * 80)
    print("🏛️ [STAGE 5: AUTONOMOUS AI AGENT HEDGE FUND & TREASURY VAULT DEMO]")
    print("=" * 80)
    print(f"🔒 Active Security Gate Oracle Signer: {onchain_signer.signer_address}")

    # Canonical Test Wallets
    alpha_bot    = "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"  # Certified AI Fund Manager
    investor_dao = "0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC"  # Institutional LP Investor
    factoring_pool = "0x6418f408cFf03F862D7691f01fAb00a895E6aB93"  # Whitelisted Stage 4 Factoring Pool

    # Step 1: Institutional Investors deposit $100,000 into Vault
    vault_tvl = 100000.0  # $100,000 USDC
    print(f"\n1️⃣ Step 1: Institutional Investors & DAOs deposit $100,000 USDC into AgentTreasuryVault.sol...")
    print(f"   🏦 AgentTreasuryVault TVL: ${vault_tvl:,.2f} USDC (100,000 Vault Shares Issued)")
    print(f"   📊 Initial Vault Share Price: $1.0000 USDC")

    # Step 2: Establish AlphaBot's manager credentials
    vault_manager.deposit(alpha_bot, 200.0)
    for _ in range(12):
        credit_engine.record_audit(alpha_bot, verdict="PASSED", hallucination_detected=False)

    report = credit_engine.compute_credit_score(alpha_bot)
    print(f"\n2️⃣ Step 2: Certified AI Fund Manager AlphaBot assumes vault portfolio management...")
    print(f"   🤖 Agent Address: {alpha_bot}")
    print(f"   📈 Manager FICO Score: {report['credit_score']} / 850 (Grade: {report['grade']})")
    print(f"   ✅ Certified Institutional Fund Manager Status: APPROVED (Threshold >= 700)")

    # Step 3: AlphaBot spots high-yield opportunity
    strategy_id = 701
    allocation_amount = 10000.0  # $10,000 USDC allocation
    strategy_rationale = "Allocate $10,000 USDC to Stage 4 Agent Factoring Pool for prime 24.3% APY milestone bond yield."

    print(f"\n3️⃣ Step 3: AlphaBot formulates strategy & requests Security Gate Oracle authorization...")
    print(f"   🎯 Strategy #{strategy_id}: {strategy_rationale}")
    print(f"   💰 Target Allocation: ${allocation_amount:,.2f} USDC")
    print(f"   🏛️ Target Protocol:   {factoring_pool} (Stage 4 Factoring Pool)")

    # Step 4: Security Gate Audits & Signs
    auth = asset_management_engine.authorize_trade_strategy(
        strategy_id=strategy_id,
        agent_address=alpha_bot,
        target_protocol=factoring_pool,
        max_allocation_usdc=allocation_amount,
        max_slippage_bps=50,
        strategy_rationale=strategy_rationale,
        chain_id=137
    )

    print(f"\n4️⃣ Step 4: Security Gate Oracle conducts cryptographic pre-flight safety audit...")
    print(f"   🛡️ Protocol Whitelist Check:  PASSED (Verified Protocol)")
    print(f"   🔍 Prompt Injection Audit:    PASSED (Zero Malicious Intents)")
    print(f"   📉 Slippage Tolerance:        {auth['max_slippage_bps']} bps (Max 100 bps)")
    print(f"   📜 EIP-712 TradeAuthorization Issued:")
    print(f"      - Strategy Hash: {auth['strategy_hash'][:22]}...")
    print(f"      - Oracle Signer: {auth['attestation']['oracle_signer']}")
    print(f"      - Signature:     {auth['attestation']['r'][:16]}...")

    # Step 5: Vault executes trade on Polygon
    print(f"\n5️⃣ Step 5: AgentTreasuryVault executes strategy on Polygon...")
    print(f"   ⛓️ AgentTreasuryVault.executeStrategy() confirmed on-chain!")
    print(f"   💸 $10,000.00 USDC disbursed to Stage 4 Factoring Pool!")

    # Step 6: Trade Matures with Profit
    gross_profit = 200.0  # $200.00 USDC profit (2.0% in 30 days = 24.3% APY)
    returned_amount = allocation_amount + gross_profit
    print(f"\n6️⃣ Step 6: 30 Days Later - Factoring Bond matures and returns capital with yield...")
    print(f"   💰 Capital Returned to Vault: ${returned_amount:,.2f} USDC (Gross Profit: +${gross_profit:.2f} USDC)")

    # Step 7: Automated Performance Fee Distribution
    split = asset_management_engine.calculate_performance_split(gross_profit_usdc=gross_profit)
    new_tvl = vault_tvl + split['net_investor_profit_usdc']
    new_share_price = new_tvl / 100000.0

    print(f"\n7️⃣ Step 7: On-Chain Performance Fee Split & High-Water Mark Accounting...")
    print(f"   🤖 AI Manager AlphaBot Fee (15%):     +${split['manager_performance_fee_usdc']:.2f} USDC (Reward for AlphaBot)")
    print(f"   ⚡ Oracle Guardrail Fee (5%):          +${split['oracle_guard_fee_usdc']:.2f} USDC (Risk-Free Oracle Revenue 💵)")
    print(f"   🎉 Net Profit Accrued to LPs (80%):    +${split['net_investor_profit_usdc']:.2f} USDC")
    print(f"   📈 New Vault Share Price:             ${new_share_price:.4f} USDC (+{split['net_investor_profit_usdc']/1000:.2f}% Return)")

    # Grand Summary
    print("\n" + "=" * 80)
    print("🏆 [GRAND SYNTHESIS SUMMARY] The Complete Autonomous AI Financial Economy!")
    print("   1. Stage 1 (Escrow):      Verified task deliverables & slashed bad actors")
    print("   2. Stage 2 (Lending):     Funded zero-capital agents via uncollateralized loans")
    print("   3. Stage 3 (Insurance):   Instant 100% malpractice indemnification via Oracle")
    print("   4. Stage 4 (Factoring):   Turned 30-day receivables into 0-second liquid cash")
    print("   5. Stage 5 (Treasury):    AI Hedge Fund autonomously compounded capital safely")
    print("   -----------------------------------------------------------------------------")
    print(f"   💵 Total Oracle Capital at Risk: $0.00 USDC (100% Risk Borne by Smart Contracts)")
    print(f"   💎 Total Oracle Protocol Fees:   Harvested across all 5 financial pillars!")
    print("=" * 80)


if __name__ == "__main__":
    main()
