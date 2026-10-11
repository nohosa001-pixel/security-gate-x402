"""
Agent Security Gate x402 - Guarded Safe Wallet Facade.
======================================================
Consolidated into `app.spend_guard`.
Maintains 100% backward-compatible imports for GuardedSafeWallet.
"""

from app.spend_guard import (
    GuardedSafeWallet,
    SpendGuard,
    spend_guard,
    SecurityGateViolationError,
    SpendLimitExceededError,
    UnboundedLoopError
)

__all__ = [
    "GuardedSafeWallet",
    "SpendGuard",
    "spend_guard",
    "SecurityGateViolationError",
    "SpendLimitExceededError",
    "UnboundedLoopError"
]
