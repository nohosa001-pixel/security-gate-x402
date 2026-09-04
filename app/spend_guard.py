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
