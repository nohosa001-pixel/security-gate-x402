__version__ = "2.1.0"

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
from app.agentkit_provider import SecurityGateAgentKitProvider
from app.solana_squads_adapter import SolanaSquadsAnchorAdapter

__all__ = [
    "spend_guard",
    "SpendGuard",
    "GuardedSafeWallet",
    "guard_automator",
    "SecurityGateMiddleware",
    "SecurityGateAgentKitProvider",
    "SolanaSquadsAnchorAdapter",
    "SecurityGateViolationError",
    "SpendLimitExceededError",
    "UnboundedLoopError",
]
