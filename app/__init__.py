"""Agent Output Security and Hallucination Gate (x402) package."""
__version__ = "1.3.0"

from app.spend_guard import (
    spend_guard,
    SpendGuard,
    SecurityGateViolationError,
    SpendLimitExceededError,
    UnboundedLoopError,
)

__all__ = [
    "spend_guard",
    "SpendGuard",
    "SecurityGateViolationError",
    "SpendLimitExceededError",
    "UnboundedLoopError",
]
