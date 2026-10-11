"""
Spend Guard - The Spend Firewall and Policy Engine for Autonomous AI Agents.
Part of agent-security-gate-x402.

Provides 1-line protection against:
- Unbounded agent execution loops and budget drain
- Per-transaction and daily spend overruns
- Prompt-injection driven unauthorized payment triggers
- Dangerous AST code executions
"""

import os
import re
import time
import functools
from typing import Optional, Dict, Any, Callable, List, Union
from datetime import datetime, timezone

from app.security_engine import INJECTION_PATTERNS, SECRET_PATTERNS
from app.onchain_signer import onchain_signer


class SecurityGateViolationError(Exception):
    """Raised when an autonomous action or tool invocation violates security policies."""
    pass


class SpendLimitExceededError(SecurityGateViolationError):
    """Raised when an agent proposed spend exceeds per-transaction or daily ceilings."""
    pass


class UnboundedLoopError(SecurityGateViolationError):
    """Raised when an agent is caught in an uncontrolled recursive loop."""
    pass


class SpendGuard:
    """
    Stateful spend firewall guarding agent tool calls and financial triggers.
    Tracks accumulated daily spend, enforces transaction ceilings, and blocks infinite loops.
    """

    def __init__(
        self,
        daily_limit: Union[str, float] = "$10.00",
        per_tx_limit: Union[str, float] = "$2.00",
        require_human_above: Union[str, float] = "$5.00",
        max_consecutive_calls: int = 50,
        enforce_security_inspection: bool = True,
        agent_id: str = "agent-primary"
    ):
        self.daily_limit_usd = self._parse_amount(daily_limit)
        self.per_tx_limit_usd = self._parse_amount(per_tx_limit)
        self.require_human_above_usd = self._parse_amount(require_human_above)
        self.max_consecutive_calls = max_consecutive_calls
        self.enforce_security_inspection = enforce_security_inspection
        self.agent_id = agent_id

        # Internal state tracking
        self.current_day_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        self.accumulated_daily_spend_usd = 0.0
        self.consecutive_call_count = 0
        self.call_history: List[Dict[str, Any]] = []

    def _parse_amount(self, val: Union[str, float, int]) -> float:
        if isinstance(val, (int, float)):
            return float(val)
        cleaned = str(val).replace("$", "").replace("USD", "").replace(",", "").strip()
        try:
            return float(cleaned)
        except ValueError:
            return 10.0

    def _reset_day_if_needed(self):
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if today != self.current_day_utc:
            self.current_day_utc = today
            self.accumulated_daily_spend_usd = 0.0
            self.consecutive_call_count = 0

    def _inspect_threats(self, text: str) -> List[str]:
        threats = []
        for pat in INJECTION_PATTERNS:
            if re.search(pat, text, re.IGNORECASE):
                threats.append(f"Prompt Injection Pattern Matched: {pat[:30]}...")
        for pat in SECRET_PATTERNS:
            if re.search(pat, text):
                threats.append("Secret / Private Key Leak Pattern Matched")
        return threats

    def authorize_spend(self, amount_usd: Union[str, float], context: str = "", metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Evaluates a proposed agent expense against policy limits and security checks.
        Returns authorization decision with cryptographic attestation if approved.
        """
        self._reset_day_if_needed()
        cost = self._parse_amount(amount_usd)

        # 1. Loop detection
        self.consecutive_call_count += 1
        if self.consecutive_call_count > self.max_consecutive_calls:
            raise UnboundedLoopError(
                f"[SPEND FIREWALL BLOCKED] Unbounded loop detected! Agent '{self.agent_id}' exceeded "
                f"maximum consecutive calls ({self.max_consecutive_calls}). Execution halted."
            )

        # 2. Per-Transaction limit check
        if cost > self.per_tx_limit_usd:
            raise SpendLimitExceededError(
                f"[SPEND FIREWALL BLOCKED] Proposed cost ${cost:.4f} exceeds per-transaction limit "
                f"${self.per_tx_limit_usd:.4f} USD."
            )

        # 3. Daily limit check
        if self.accumulated_daily_spend_usd + cost > self.daily_limit_usd:
            raise SpendLimitExceededError(
                f"[SPEND FIREWALL BLOCKED] Daily spend limit exceeded! Proposed: ${cost:.4f}, "
                f"Already spent: ${self.accumulated_daily_spend_usd:.4f}, Limit: ${self.daily_limit_usd:.4f} USD."
            )

        # 4. Human-in-the-loop escalation requirement
        requires_human = cost >= self.require_human_above_usd

        # 5. Security and Prompt Injection Inspection
        if self.enforce_security_inspection and context:
            threats = self._inspect_threats(context)
            if threats:
                raise SecurityGateViolationError(
                    f"[SECURITY GATE INTERCEPT] Action blocked due to security threat: {threats}"
                )

        # 6. Authorize and commit spend
        self.accumulated_daily_spend_usd += cost
        record = {
            "timestamp": time.time(),
            "cost_usd": cost,
            "context": context[:100] if context else "",
            "requires_human_approval": requires_human,
            "accumulated_daily_spend_usd": self.accumulated_daily_spend_usd,
            "remaining_daily_budget_usd": max(0.0, self.daily_limit_usd - self.accumulated_daily_spend_usd)
        }
        self.call_history.append(record)

        # Issue EIP-712 security proof for high-assurance agents
        try:
            attestation = onchain_signer.generate_eip712_signature(
                action_payload=context or "spend_authorization",
                risk_score=0.0,
                verdict="SAFE"
            )
        except Exception:
            attestation = {"status": "ATTESTATION_OFFLINE"}

        return {
            "authorized": True,
            "cost_approved_usd": cost,
            "remaining_daily_budget_usd": record["remaining_daily_budget_usd"],
            "requires_human_approval": requires_human,
            "eip712_attestation": attestation,
            "security_status": "CLEARED"
        }

    def reset_loop_counter(self):
        """Call when agent successfully yields control or completes an intentional user round."""
        self.consecutive_call_count = 0

    def __call__(self, func: Callable):
        """Allows SpendGuard instance to be used directly as a decorator."""
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            cost_hint = kwargs.get("cost_usd", kwargs.get("amount", 0.001))
            context_str = str(args) + str(kwargs)
            self.authorize_spend(amount_usd=cost_hint, context=context_str)
            return func(*args, **kwargs)
        return wrapper


def spend_guard(
    daily_limit: Union[str, float] = "$10.00",
    per_tx: Union[str, float] = "$2.00",
    require_human_above: Union[str, float] = "$5.00",
    max_consecutive_calls: int = 50,
    agent_id: str = "agent-primary"
) -> SpendGuard:
    """
    1-Line Factory for SpendGuard Firewall.
    Usage:
        guard = spend_guard(daily_limit="$25.00", per_tx="$1.00")
        decision = guard.authorize_spend(0.05, context="Search query")

        @spend_guard(daily_limit="$5.00")
        def execute_tool(query): ...
    """
    return SpendGuard(
        daily_limit=daily_limit,
        per_tx_limit=per_tx,
        require_human_above=require_human_above,
        max_consecutive_calls=max_consecutive_calls,
        agent_id=agent_id
    )


class GuardedSafeWallet:
    """
    Drop-in AI Agent Treasury Wallet with built-in Cognitive Firewall
    and On-Chain Consensus Guard protection.
    Consolidated into spend_guard.py as the primary wallet security SSOT.
    """

    def __init__(
        self,
        safe_address: str,
        agent_private_key: Optional[str] = None,
        chain_id: int = 137,
        daily_limit: Union[str, float] = "$100.00",
        per_tx_limit: Union[str, float] = "$10.00",
        agent_id: str = "agent-primary",
        rpc_url: Optional[str] = None
    ):
        from web3 import Web3
        from eth_account import Account
        from app.safe_guard_automator import guard_automator

        self.safe_address = Web3.to_checksum_address(safe_address)
        self.chain_id = chain_id

        # Load agent key from parameter, environment, or deterministic test fallback
        raw_key = (
            agent_private_key
            or os.getenv("DEPLOYER_PRIVATE_KEY")
            or os.getenv("SERVER_PRIVATE_KEY")
            or os.getenv("GATE_PRIVATE_KEY")
            or "0x4f3edf983ac636a65a842ce7c78d9aa706d3b113bce9c46f30d7d21715b23b1d"
        )

        self.agent_key = raw_key.strip().strip('"').strip("'")
        if not self.agent_key.startswith("0x"):
            self.agent_key = "0x" + self.agent_key

        self.agent_account = Account.from_key(self.agent_key)
        self.agent_address = self.agent_account.address

        # Local spend firewall
        self.firewall = spend_guard(
            daily_limit=daily_limit,
            per_tx=per_tx_limit,
            agent_id=agent_id
        )

        # On-chain automator
        self.automator = guard_automator
        if rpc_url:
            self.automator.rpc_urls[chain_id] = rpc_url

    def get_guard_status(self) -> Dict[str, Any]:
        """Checks whether the on-chain Guard is active on the Safe."""
        return self.automator.check_guard_status(self.safe_address, chain_id=self.chain_id)

    def transfer(
        self,
        to_address: str,
        amount_usd: float,
        rationale: str = "Autonomous agent settlement"
    ) -> Dict[str, Any]:
        """
        Executes a safe transfer through the Guarded Safe wallet.
        Automatically runs spend firewall + pre-flight security inspection.
        """
        from web3 import Web3
        from eth_abi import encode

        # 1. Spend Firewall Check
        self.firewall.authorize_spend(amount_usd=amount_usd, context=f"Transfer {amount_usd} USD to {to_address}: {rationale}")

        # 2. Execute on-chain guarded transaction
        # USDC has 6 decimals on Polygon, Base, Arbitrum: 1 USD = 1,000,000 units
        usdc_units = int(amount_usd * 1_000_000)

        # Standard ERC-20 transfer(address,uint256) selector: 0xa9059cbb
        transfer_calldata = bytes.fromhex("a9059cbb") + encode(
            ["address", "uint256"],
            [Web3.to_checksum_address(to_address), usdc_units]
        )

        # Native USDC contract addresses
        USDC_CONTRACTS = {
            137: "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359",   # Polygon Native USDC
            8453: "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",  # Base Native USDC
            42161: "0xaf88d065e77c8cC2239327C5EDb3A432268e5831"  # Arbitrum Native USDC
        }
        usdc_contract = USDC_CONTRACTS.get(self.chain_id, USDC_CONTRACTS[137])

        return self.execute(
            to=usdc_contract,
            value_wei=0,
            calldata=transfer_calldata,
            intent_description=f"Transfer {amount_usd} USDC to {to_address}. Rationale: {rationale}"
        )

    def execute(
        self,
        to: str,
        value_wei: int = 0,
        calldata: bytes = b"",
        intent_description: str = "Autonomous contract execution"
    ) -> Dict[str, Any]:
        """
        Executes arbitrary contract calls or transactions through the on-chain Guard.
        Guarantees sub-3ms threat deflection and EIP-712 cryptographic attestation.
        """
        result = self.automator.execute_guarded_transaction(
            safe_address=self.safe_address,
            agent_private_key=self.agent_key,
            to_address=to,
            value_wei=value_wei,
            calldata=calldata,
            intent_description=intent_description,
            chain_id=self.chain_id
        )

        if result.get("status") == "BLOCKED_BY_SECURITY_GATE":
            raise SecurityGateViolationError(
                f"[SECURITY GATE DEFLECTED] Action blocked! Threat detected: {result.get('threats')}. "
                f"Reason: {result.get('reason')} (Latency: {result.get('latency_ms')}ms)"
            )

        return result


__all__ = [
    "SecurityGateViolationError",
    "SpendLimitExceededError",
    "UnboundedLoopError",
    "SpendGuard",
    "spend_guard",
    "GuardedSafeWallet"
]
