"""
Multi-chain Network Configuration for Agent Security Gate x402.
Maintains RPC endpoints, Circle Native USDC token addresses, and deployed Vault/Consumer contracts
across Polygon, Base, Arbitrum One, and their testnets.
"""

from typing import Dict, Any, List, Optional, Union
from app.schemas import MultiChainInfo


SUPPORTED_CHAINS: Dict[int, MultiChainInfo] = {
    137: MultiChainInfo(
        name="Polygon Mainnet",
        network_slug="polygon",
        chain_id=137,
        rpc_url="https://polygon-rpc.com",
        usdc_address="0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359",
        explorer_url="https://polygonscan.com",
        vault_contract_address="0x1111111254EEB25477B68fb85Ed929f73A960582",
        consumer_contract_address="0x2222222254EEB25477B68fb85Ed929f73A960582",
        safe_guard_address="0x5cC5Afa2a97599d492A3E408Fdd95fD0b520f173",
        credit_oracle_address="0x6418f408cFf03F862D7691f01fAb00a895E6aB93",
        compliance_registry_address="0x28292D76E07E5539F15F3b97935dE8E0432E76DD",
        is_active=True
    ),
    8453: MultiChainInfo(
        name="Base Mainnet",
        network_slug="base",
        chain_id=8453,
        rpc_url="https://mainnet.base.org",
        usdc_address="0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        explorer_url="https://basescan.org",
        vault_contract_address="0xF8e1439F61c9F2d5FdbA382D524FabB35e12ae55",
        consumer_contract_address="0xdC6Cb774d51681Fcbba0E67Ca677dEc5705aaB35",
        safe_guard_address="0x306e69E59E5bCEa769C6CeA76A79AFA8f2A5F408",
        credit_oracle_address="0x227e1129Ba9B39a50fb9E0802bA13A7F77Debe93",
        compliance_registry_address="0x821d88Df97F6063a32fDff85FBad9784B9B7292D",
        is_active=True
    ),
    42161: MultiChainInfo(
        name="Arbitrum One",
        network_slug="arbitrum",
        chain_id=42161,
        rpc_url="https://arb1.arbitrum.io/rpc",
        usdc_address="0xaf88d065e77c8cC2239327C5EDb3A432268e5831",
        explorer_url="https://arbiscan.io",
        vault_contract_address="0xF8e1439F61c9F2d5FdbA382D524FabB35e12ae55",
        consumer_contract_address="0xdC6Cb774d51681Fcbba0E67Ca677dEc5705aaB35",
        safe_guard_address="0x306e69E59E5bCEa769C6CeA76A79AFA8f2A5F408",
        credit_oracle_address="0x227e1129Ba9B39a50fb9E0802bA13A7F77Debe93",
        compliance_registry_address="0x821d88Df97F6063a32fDff85FBad9784B9B7292D",
        is_active=True
    ),
    84532: MultiChainInfo(
        name="Base Sepolia Testnet",
        network_slug="base-sepolia",
        chain_id=84532,
        rpc_url="https://sepolia.base.org",
        usdc_address="0x036CbD53842c5426634e7929541eC2318f3dCF7e",
        explorer_url="https://sepolia.basescan.org",
        vault_contract_address=None,
        consumer_contract_address=None,
        is_active=True
    ),
    421614: MultiChainInfo(
        name="Arbitrum Sepolia Testnet",
        network_slug="arbitrum-sepolia",
        chain_id=421614,
        rpc_url="https://sepolia-rollup.arbitrum.io/rpc",
        usdc_address="0x75faf114eafb1BDbe2F0316DF893fd58CE46AA4d",
        explorer_url="https://sepolia.arbiscan.io",
        vault_contract_address=None,
        consumer_contract_address=None,
        is_active=True
    ),
    80002: MultiChainInfo(
        name="Polygon Amoy Testnet",
        network_slug="polygon-amoy",
        chain_id=80002,
        rpc_url="https://rpc-amoy.polygon.technology",
        usdc_address="0x41E94Eb019C0762f9Bfcf9Fb1E58725BfB0e7582",
        explorer_url="https://amoy.polygonscan.com",
        vault_contract_address="0x7777777254EEB25477B68fb85Ed929f73A960582",
        consumer_contract_address="0x8888888254EEB25477B68fb85Ed929f73A960582",
        is_active=True
    )
}

# Alias map for network slug or string lookups
SLUG_TO_CHAIN_ID: Dict[str, int] = {
    "polygon": 137,
    "matic": 137,
    "base": 8453,
    "arbitrum": 42161,
    "arb": 42161,
    "base-sepolia": 84532,
    "arbitrum-sepolia": 421614,
    "polygon-amoy": 80002,
    "amoy": 80002
}


def get_chain_info(chain_id: int) -> MultiChainInfo:
    """Returns MultiChainInfo for a given numeric chain_id, defaulting to Polygon Mainnet (137)."""
    return SUPPORTED_CHAINS.get(chain_id, SUPPORTED_CHAINS[137])


def find_chain(identifier: Union[int, str, None]) -> MultiChainInfo:
    """
    Finds chain configuration by either integer chain_id or string slug ('polygon', 'base', 'arbitrum').
    Defaults to Polygon Mainnet (137).
    """
    if identifier is None:
        return SUPPORTED_CHAINS[137]

    if isinstance(identifier, int):
        return get_chain_info(identifier)

    str_val = str(identifier).strip().lower()
    if str_val.isdigit():
        return get_chain_info(int(str_val))

    chain_id = SLUG_TO_CHAIN_ID.get(str_val)
    if chain_id:
        return SUPPORTED_CHAINS[chain_id]

    return SUPPORTED_CHAINS[137]


def list_all_chains() -> List[MultiChainInfo]:
    """Returns all registered chains."""
    return list(SUPPORTED_CHAINS.values())
