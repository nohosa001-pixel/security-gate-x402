"""
Multi-chain Network Configuration for Agent Security Gate x402.
Maintains RPC endpoints, USDC token addresses, and deployed Vault/Consumer contracts
across Polygon, Base, Arbitrum, and Ethereum.
"""

from typing import Dict, Any, List
from app.schemas import MultiChainInfo


SUPPORTED_CHAINS: Dict[int, MultiChainInfo] = {
    137: MultiChainInfo(
        name="Polygon Mainnet",
        chain_id=137,
        rpc_url="https://polygon-rpc.com",
        usdc_address="0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359",
        vault_contract_address="0x1111111254EEB25477B68fb85Ed929f73A960582",
        consumer_contract_address="0x2222222254EEB25477B68fb85Ed929f73A960582",
        safe_guard_address="0x5cC5Afa2a97599d492A3E408Fdd95fD0b520f173",
        credit_oracle_address="0x6418f408cFf03F862D7691f01fAb00a895E6aB93",
        compliance_registry_address="0x28292D76E07E5539F15F3b97935dE8E0432E76DD",
        is_active=True
    ),
    8453: MultiChainInfo(
        name="Base Mainnet",
        chain_id=8453,
        rpc_url="https://mainnet.base.org",
        usdc_address="0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        vault_contract_address="0x3333333254EEB25477B68fb85Ed929f73A960582",
        consumer_contract_address="0x4444444254EEB25477B68fb85Ed929f73A960582",
        is_active=True
    ),
    42161: MultiChainInfo(
        name="Arbitrum One",
        chain_id=42161,
        rpc_url="https://arb1.arbitrum.io/rpc",
        usdc_address="0xaf88d065e77c8cC2239327C5EDb3A432268e5831",
        vault_contract_address="0x5555555254EEB25477B68fb85Ed929f73A960582",
        consumer_contract_address="0x6666666254EEB25477B68fb85Ed929f73A960582",
        is_active=True
    ),
    80002: MultiChainInfo(
        name="Polygon Amoy Testnet",
        chain_id=80002,
        rpc_url="https://rpc-amoy.polygon.technology",
        usdc_address="0x41E94Eb019C0762f9Bfcf9Fb1E58725BfB0e7582",
        vault_contract_address="0x7777777254EEB25477B68fb85Ed929f73A960582",
        consumer_contract_address="0x8888888254EEB25477B68fb85Ed929f73A960582",
        is_active=True
    )
}


def get_chain_info(chain_id: int) -> MultiChainInfo:
    return SUPPORTED_CHAINS.get(chain_id, SUPPORTED_CHAINS[137])


def list_all_chains() -> List[MultiChainInfo]:
    return list(SUPPORTED_CHAINS.values())
