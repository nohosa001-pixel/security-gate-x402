"""
Agent Payment Vault Manager for Agent Security Gate x402.
Maintains in-memory and persisted pre-funded agent USDC balances for zero-latency (<1ms) querying.
Supports unlimited deposit amounts (micro-amounts to millions of USDC) and high-throughput M2M agent traffic.
"""

import json
import os
import secrets
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from eth_utils import to_checksum_address
from pydantic import BaseModel


class AgentVaultAccount(BaseModel):
    agent_address: str
    balance_usdc: float
    total_deposited_usdc: float
    total_consumed_usdc: float
    session_key: str
    created_at_utc: str
    last_active_utc: str
    query_count: int = 0


class VaultManager:
    """Thread-safe manager for pre-funded agent payment vault accounts with persistence."""

    def __init__(self, state_file_path: Optional[str] = None):
        self._lock = threading.Lock()
        # agent_address (checksummed) -> AgentVaultAccount
        self._accounts: Dict[str, AgentVaultAccount] = {}
        # session_key -> agent_address
        self._session_index: Dict[str, str] = {}
        
        # Persistence path
        default_state_path = Path(__file__).parent.parent / "data" / "vault_state.json"
        self._state_file = Path(state_file_path or os.getenv("VAULT_STATE_FILE", str(default_state_path)))
        
        # Load persisted accounts if exists, else seed demo account
        self._load_state()
        self._seed_demo_account()

    def _seed_demo_account(self):
        try:
            demo_addr = to_checksum_address("0x70997970C51812dc3A010C7d01b50e0d17dc79C8")
        except Exception:
            demo_addr = "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"
        demo_key = "vault_key_security_demo_agent_2026"
        now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        with self._lock:
            if demo_addr not in self._accounts:
                acc = AgentVaultAccount(
                    agent_address=demo_addr,
                    balance_usdc=50.00,  # $50.00 USDC pre-funded sandbox balance
                    total_deposited_usdc=50.00,
                    total_consumed_usdc=0.0,
                    session_key=demo_key,
                    created_at_utc=now_iso,
                    last_active_utc=now_iso,
                    query_count=0,
                )
                self._accounts[demo_addr] = acc
                self._session_index[demo_key] = demo_addr

    def _save_state(self):
        """Saves current vault state to disk safely (non-blocking errors)."""
        try:
            self._state_file.parent.mkdir(parents=True, exist_ok=True)
            data = {
                addr: acc.model_dump() for addr, acc in self._accounts.items()
            }
            tmp_file = self._state_file.with_suffix(".tmp")
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            tmp_file.replace(self._state_file)
        except Exception:
            pass  # Fail gracefully in read-only / serverless scratch environments

    def _load_state(self):
        """Loads vault state from disk if available."""
        try:
            if self._state_file.exists():
                with open(self._state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                with self._lock:
                    for addr, acc_data in data.items():
                        acc = AgentVaultAccount(**acc_data)
                        self._accounts[addr] = acc
                        self._session_index[acc.session_key] = addr
        except Exception:
            pass

    def deposit(self, agent_address: str, amount_usdc: float) -> AgentVaultAccount:
        """
        Deposits USDC into an agent's pre-funded vault balance.
        Minimum deposit: $50.00 USDC (unlimited upper ceiling up to millions of USDC).
        """
        if amount_usdc < 50.0:
            raise ValueError("Minimum deposit amount is $50.00 USDC.")

        try:
            checksum_addr = to_checksum_address(agent_address)
        except Exception:
            checksum_addr = agent_address.lower()

        now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        with self._lock:
            if checksum_addr in self._accounts:
                acc = self._accounts[checksum_addr]
                acc.balance_usdc = round(acc.balance_usdc + amount_usdc, 6)
                acc.total_deposited_usdc = round(acc.total_deposited_usdc + amount_usdc, 6)
                acc.last_active_utc = now_iso
                ret = acc
            else:
                session_key = f"vault_key_{secrets.token_hex(16)}"
                acc = AgentVaultAccount(
                    agent_address=checksum_addr,
                    balance_usdc=round(amount_usdc, 6),
                    total_deposited_usdc=round(amount_usdc, 6),
                    total_consumed_usdc=0.0,
                    session_key=session_key,
                    created_at_utc=now_iso,
                    last_active_utc=now_iso,
                    query_count=0,
                )
                self._accounts[checksum_addr] = acc
                self._session_index[session_key] = checksum_addr
                ret = acc

        self._save_state()
        return ret

    def deduct(self, session_or_addr: str, cost_usdc: float = 0.002) -> Tuple[bool, str, float]:
        """
        Deducts inspection cost from the vault account in sub-millisecond time.
        Returns: (success: bool, reason_or_agent_addr: str, remaining_balance: float)
        """
        now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        with self._lock:
            # Resolve target account
            agent_addr = None
            if session_or_addr in self._session_index:
                agent_addr = self._session_index[session_or_addr]
            elif session_or_addr in self._accounts:
                agent_addr = session_or_addr
            else:
                try:
                    c_addr = to_checksum_address(session_or_addr)
                    if c_addr in self._accounts:
                        agent_addr = c_addr
                except Exception:
                    pass

            if not agent_addr or agent_addr not in self._accounts:
                return False, "Vault account not found.", 0.0

            acc = self._accounts[agent_addr]
            if acc.balance_usdc < cost_usdc:
                return False, f"Insufficient balance ({acc.balance_usdc:.4f} USDC < {cost_usdc} USDC). Please deposit funds.", acc.balance_usdc

            acc.balance_usdc = round(acc.balance_usdc - cost_usdc, 6)
            acc.total_consumed_usdc = round(acc.total_consumed_usdc + cost_usdc, 6)
            acc.query_count += 1
            acc.last_active_utc = now_iso
            ret = (True, agent_addr, acc.balance_usdc)

        # Periodic / quick state sync
        if acc.query_count % 50 == 0:
            self._save_state()

        return ret

    def get_account(self, session_or_addr: str) -> Optional[AgentVaultAccount]:
        with self._lock:
            if session_or_addr in self._session_index:
                agent_addr = self._session_index[session_or_addr]
                return self._accounts.get(agent_addr)
            if session_or_addr in self._accounts:
                return self._accounts[session_or_addr]
            try:
                c_addr = to_checksum_address(session_or_addr)
                return self._accounts.get(c_addr)
            except Exception:
                return None


vault_manager = VaultManager()
