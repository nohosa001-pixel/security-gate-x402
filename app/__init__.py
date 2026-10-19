__version__ = "2.0.0"

from app.spend_guard import (
    spend_guard,
    SpendGuard,
    SecurityGateViolationError,
    SpendLimitExceededError,
    UnboundedLoopError,
)
from app.guarded_wallet import GuardedSafeWallet
from app.safe_guard_automator import guard_automator
from app.security_gate_middleware import SecurityGateMiddleware

__all__ = [
    "spend_guard",
    "SpendGuard",
    "GuardedSafeWallet",
    "guard_automator",
    "SecurityGateMiddleware",
    "SecurityGateViolationError",
    "SpendLimitExceededError",
    "UnboundedLoopError",
]
