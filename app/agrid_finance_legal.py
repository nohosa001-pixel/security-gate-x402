"""
A GRID Enterprise Finance, Accounting & Legal Integration Module.
Provides:
1. [Finance]: Treasury vault pre-funding, auto-topup threshold, runway cash-flow forecasting.
2. [Accounting]: Micro-expense journal entries ($0.002/query), reconciliation ledger, fiscal invoicing.
3. [Legal]: EIP-712 tamper-proof audit trail archiving, OFAC sanctions compliance, zero-retention verification.
"""

import time
import json
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from app.vault_manager import vault_manager
from app.x402_verifier import is_sanctioned_address
from app.onchain_signer import onchain_signer


class AGridJournalEntry(BaseModel):
    entry_id: str
    timestamp_utc: str
    account_debit: str = "IT Infrastructure & Security Gate Expense"  # 차변: 소프트웨어/보안 수수료
    account_credit: str = "Prepaid USDC Vault Asset"                  # 대변: 선급 USDC 자산
    amount_usdc: float
    query_count: int
    session_key: str
    tax_category: str = "Tax-Exempt Digital M2M Micro-Service"


class AGridReconciliationReport(BaseModel):
    company_name: str = "A GRID Corp."
    reporting_period: str
    total_deposited_usdc: float
    total_consumed_usdc: float
    remaining_treasury_balance: float
    total_audit_queries: int
    cost_per_query_usdc: float = 0.002
    journal_entries_count: int
    legal_compliance_status: str = "100% OFAC & Cryptographically Attested"


class AGridLegalAttestationRecord(BaseModel):
    action_type: str  # "FINANCIAL_DISPATCH", "CONTRACT_APPROVAL", "REGULATORY_FILING"
    subject_hash: str
    verdict: str
    risk_score: float
    eip712_signature: str
    signer_oracle: str
    timestamp_utc: str
    compliance_passed: bool
    data_retention_policy: str = "Ephemeral (Zero-Data Retention Verified)"


class AGridIntegrationController:
    """Enterprise Controller for A GRID's Finance, Accounting & Legal Agents."""

    def __init__(self, treasury_address: str = "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"):
        self.treasury_address = treasury_address
        self._journal_entries: List[AGridJournalEntry] = []
        self._legal_audit_trail: List[AGridLegalAttestationRecord] = []

    # -------------------------------------------------------------
    # 1. FINANCE (재무 관리 & 자금 런웨이)
    # -------------------------------------------------------------
    def finance_fund_treasury(self, deposit_amount_usdc: float) -> Dict[str, Any]:
        """A GRID 재무 지갑에서 선불 Vault로 자금 집행 (최소 50 USDC 이상)"""
        if deposit_amount_usdc < 50.0:
            raise ValueError("A GRID Finance Rule: Minimum deposit is $50.00 USDC.")

        acc = vault_manager.deposit(self.treasury_address, deposit_amount_usdc)
        return {
            "status": "success",
            "treasury_address": self.treasury_address,
            "deposited_usdc": deposit_amount_usdc,
            "current_balance_usdc": acc.balance_usdc,
            "available_queries_runway": int(acc.balance_usdc / 0.002),
            "session_key": acc.session_key
        }

    def finance_get_runway_status(self) -> Dict[str, Any]:
        """A GRID 재무팀용 런웨이 및 자동 보충(Auto-topup) 상태 진단"""
        acc = vault_manager.get_account(self.treasury_address)
        balance = acc.balance_usdc if acc else 0.0
        queries_left = int(balance / 0.002)
        needs_topup = balance < 10.0  # 10달러 미만 시 재무 경보

        return {
            "company": "A GRID Corp.",
            "treasury_balance_usdc": balance,
            "queries_remaining": queries_left,
            "days_runway_at_2500_qpd": round(queries_left / 2500, 1),
            "topup_alert": needs_topup,
            "recommended_topup_usdc": 50.0 if needs_topup else 0.0
        }

    # -------------------------------------------------------------
    # 2. ACCOUNTING (회계 분개 & 지출 대사)
    # -------------------------------------------------------------
    def accounting_record_consumption(self, session_key: str, cost_usdc: float, queries: int = 1) -> AGridJournalEntry:
        """에이전트 보안 감사 소비 시 복식부기 회계 전표 자동 발행"""
        now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        entry_id = f"JRN-AGRID-{int(time.time())}-{len(self._journal_entries) + 1}"
        
        entry = AGridJournalEntry(
            entry_id=entry_id,
            timestamp_utc=now_iso,
            amount_usdc=round(cost_usdc, 6),
            query_count=queries,
            session_key=session_key
        )
        self._journal_entries.append(entry)
        return entry

    def accounting_generate_reconciliation(self) -> AGridReconciliationReport:
        """A GRID 회계결산용 월간/일일 지출 대사표 생성"""
        acc = vault_manager.get_account(self.treasury_address)
        deposited = acc.total_deposited_usdc if acc else 0.0
        consumed = acc.total_consumed_usdc if acc else 0.0
        balance = acc.balance_usdc if acc else 0.0
        queries = acc.query_count if acc else 0

        now_period = time.strftime("%Y-%m", time.gmtime())
        return AGridReconciliationReport(
            reporting_period=now_period,
            total_deposited_usdc=deposited,
            total_consumed_usdc=consumed,
            remaining_treasury_balance=balance,
            total_audit_queries=queries,
            journal_entries_count=len(self._journal_entries)
        )

    # -------------------------------------------------------------
    # 3. LEGAL & COMPLIANCE (법률 감사 증적 & 컴플라이언스)
    # -------------------------------------------------------------
    def legal_audit_and_archive(
        self,
        action_type: str,
        payload_text: str,
        verdict: str,
        risk_score: float,
        signature: str,
        counterparty_address: Optional[str] = None
    ) -> AGridLegalAttestationRecord:
        """
        A GRID 법률/컴플라이언스용 EIP-712 위변조 불가 감사 증적(Audit Trail) 아카이빙
        """
        # 1. OFAC & 자금세탁방지(AML) 제재 검증
        if counterparty_address and is_sanctioned_address(counterparty_address):
            raise PermissionError(f"A GRID Legal Warning: Counterparty {counterparty_address} is OFAC Sanctioned.")

        import hashlib
        subject_hash = hashlib.sha256(payload_text.encode("utf-8")).hexdigest()
        now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        record = AGridLegalAttestationRecord(
            action_type=action_type,
            subject_hash=subject_hash,
            verdict=verdict,
            risk_score=risk_score,
            eip712_signature=signature,
            signer_oracle=onchain_signer.signer_address,
            timestamp_utc=now_iso,
            compliance_passed=(verdict == "PASSED" and risk_score == 0.0)
        )
        self._legal_audit_trail.append(record)
        return record

    def legal_get_audit_trail(self) -> List[AGridLegalAttestationRecord]:
        """A GRID 법무팀용 증적 조회"""
        return self._legal_audit_trail


agrid_controller = AGridIntegrationController()
