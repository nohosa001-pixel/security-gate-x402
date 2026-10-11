"""
Agent Security Gate x402 - Plugin: DePIN Compute & Energy Grid Truth Oracle
===========================================================================
Integrates Power Grid telemetry (voltage/frequency 50/60Hz, REC proofs) and GPU compute convergence proofs.
"""

from app.power_grid_oracle import power_grid_oracle, PowerGridOracle

__all__ = [
    "power_grid_oracle",
    "PowerGridOracle"
]
