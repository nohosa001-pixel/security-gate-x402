"""
Phase 2 Multi-Chain & Routing Tests: Polygon, Base, Arbitrum network configs and routing.
"""

import pytest
from app.multi_chain import list_all_chains, get_chain_info
from app.schemas import MultiChainInfo


def test_list_all_chains():
    chains = list_all_chains()
    assert len(chains) >= 3
    chain_ids = [c.chain_id for c in chains]
    assert 137 in chain_ids     # Polygon
    assert 8453 in chain_ids    # Base
    assert 42161 in chain_ids   # Arbitrum


def test_get_chain_info_polygon():
    info = get_chain_info(137)
    assert info.name == "Polygon Mainnet"
    assert info.usdc_address.startswith("0x")
    assert info.is_active is True


def test_get_chain_info_base():
    info = get_chain_info(8453)
    assert info.name == "Base Mainnet"
    assert info.rpc_url == "https://mainnet.base.org"


def test_get_chain_info_fallback():
    info = get_chain_info(999999)
    assert info.chain_id == 137  # Fallback to Polygon default
