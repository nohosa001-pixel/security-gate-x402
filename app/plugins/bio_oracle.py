"""
Agent Security Gate x402 - Plugin: Bio & Pharma IP Transfer Truth Oracle
========================================================================
Integrates Zero-Knowledge Proof (ZK-SNARK) verification of binding affinity Kd and TEE enclave matches.
"""

from app.truth_adapters.bio_zk_adapter import bio_zk_adapter, BioZkAdapter

__all__ = [
    "bio_zk_adapter",
    "BioZkAdapter"
]
