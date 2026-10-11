"""
Agent Security Gate x402 - Agent Credit Scoring & DID Reputation Facade.
========================================================================
Consolidated into `app.credit_rating_engine`.
Maintains 100% backward-compatible imports for DePIN compute credit scoring
and EIP-712 credit attestation issuing.
"""

from app.credit_rating_engine import (
    AgentCreditRatingEngine,
    AgentCreditEngine,
    credit_engine,
    agent_credit_engine
)

__all__ = [
    "AgentCreditRatingEngine",
    "AgentCreditEngine",
    "credit_engine",
    "agent_credit_engine"
]
