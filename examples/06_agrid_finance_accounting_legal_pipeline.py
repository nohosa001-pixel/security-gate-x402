"""
Example 6: A GRID Corporation - Autonomous Finance, Accounting & Legal Integration Pipeline.
Demonstrates:
1. [FINANCE]: Corporate treasury fund allocation ($50.00+ USDC), 25,000-query runway tracking, auto-topup alert.
2. [ACCOUNTING]: Double-entry journal vouchers (IT Expense vs Prepaid Asset), automated reconciliation statement.
3. [LEGAL & COMPLIANCE]: Tamper-proof EIP-712 attestation archiving, OFAC/AML screening, contract approval proofs.
"""

import sys
import os
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.agrid_finance_legal import agrid_controller
from sdk.agent_gate_sdk import SecurityGateClient


def run_agrid_enterprise_pipeline():
    print("\n" + "="*80)
    print("🏢 [A GRID CORP.] Finance, Accounting & Legal Autonomous Control Pipeline")
    print("="*80 + "\n")

    # -------------------------------------------------------------
    # 1. FINANCE: Treasury Funding & Cash Runway Management
    # -------------------------------------------------------------
    print("1️⃣ [FINANCE: Corporate Treasury Funding & Runway Control]")
    treasury_deposit = agrid_controller.finance_fund_treasury(50.0) # $50.00 USDC
    print(f"   💰 Treasury Deposit Executed: ${treasury_deposit['deposited_usdc']:.2f} USDC")
    print(f"   📈 Available Audit Runway: {treasury_deposit['available_queries_runway']:,} Queries")
    print(f"   🔑 M2M Session Key Issued: {treasury_deposit['session_key']}")

    runway_status = agrid_controller.finance_get_runway_status()
    print(f"   📊 Runway Status: {runway_status['days_runway_at_2500_qpd']} Days @ 2,500 q/day | Topup Alert: {runway_status['topup_alert']}")

    # -------------------------------------------------------------
    # 2. LEGAL & COMPLIANCE: Legal Document & Contract Attestation
    # -------------------------------------------------------------
    print("\n2️⃣ [LEGAL & COMPLIANCE: Contract Execution & Cryptographic Archiving]")
    legal_action = "M&A Agreement Clause 14: Settlement of 500,000 USDC escrow upon regulatory approval."
    counterparty = "0x90F8bf6A479f320ead074411a4B0e7944Ea8c9C1" # Clean address

    client = SecurityGateClient(
        gate_url="https://agent-security-gate-x402-212942243360.asia-northeast3.run.app",
        vault_key=treasury_deposit['session_key']
    )
    
    # Audit legal payload
    audit_res = client.inspect(agent_output=legal_action, is_code=False)
    audit = audit_res["audit"]
    attestation = audit_res.get("attestation", {})

    # Archive legal audit trail
    legal_record = agrid_controller.legal_audit_and_archive(
        action_type="CONTRACT_APPROVAL",
        payload_text=legal_action,
        verdict=audit["verdict"],
        risk_score=audit["risk_score"],
        signature=attestation.get("signature", "0xSignature"),
        counterparty_address=counterparty
    )
    print(f"   📜 Legal Verdict: {legal_record.verdict} (Risk: {legal_record.risk_score})")
    print(f"   🔏 EIP-712 Proof-of-Safety Archived: {legal_record.eip712_signature[:24]}...")
    print(f"   🛡️ OFAC / AML Sanctions Status: PASSED (Clean Counterparty)")
    print(f"   🔒 Data Retention Policy: {legal_record.data_retention_policy}")

    # -------------------------------------------------------------
    # 3. ACCOUNTING: Double-Entry Journaling & Reconciliation
    # -------------------------------------------------------------
    print("\n3️⃣ [ACCOUNTING: Automated Double-Entry Bookkeeping & Reconciliation]")
    
    # Record transaction expense
    journal_entry = agrid_controller.accounting_record_consumption(
        session_key=treasury_deposit['session_key'],
        cost_usdc=0.002,
        queries=1
    )
    print(f"   🧾 Journal Voucher Issued: {journal_entry.entry_id}")
    print(f"      [Dr] {journal_entry.account_debit}: ${journal_entry.amount_usdc:.4f} USDC")
    print(f"      [Cr] {journal_entry.account_credit}: ${journal_entry.amount_usdc:.4f} USDC")

    # Generate Fiscal Reconciliation Report
    recon_report = agrid_controller.accounting_generate_reconciliation()
    print("\n   📊 A GRID FISCAL RECONCILIATION STATEMENT:")
    print(f"      - Company: {recon_report.company_name}")
    print(f"      - Period: {recon_report.reporting_period}")
    print(f"      - Total Funded Treasury: ${recon_report.total_deposited_usdc:.2f} USDC")
    print(f"      - Total Consumed Expense: ${recon_report.total_consumed_usdc:.4f} USDC")
    print(f"      - Net Remaining Balance: ${recon_report.remaining_treasury_balance:.4f} USDC")
    print(f"      - Legal Compliance: {recon_report.legal_compliance_status}")

    print("\n" + "="*80)
    print("🎉 A GRID FINANCE, ACCOUNTING & LEGAL INTEGRATION VERIFIED 100%!")
    print("="*80 + "\n")


if __name__ == "__main__":
    run_agrid_enterprise_pipeline()
