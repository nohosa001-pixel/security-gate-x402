"""
Automated Contract Verification & Public Explorer Disclosure Script.
Supports Polygonscan (137), BaseScan (8453), and Arbiscan (42161).
Follows the standard established in minerals-oracle-x402.
"""

import os
import sys
import json
import argparse
from pathlib import Path
from dotenv import load_dotenv
from eth_abi import encode

ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / ".env")

CONTRACTS_DIR = ROOT_DIR / "contracts"
VERIFICATION_DIR = CONTRACTS_DIR / "verification"

# Oracle & Treasury Signer (default deployer address)
ORACLE_SIGNER = os.getenv("SERVER_WALLET_ADDRESS", "0x255F9991233f86B29dB847c8d5b8CB9915e80dCf")
TREASURY = os.getenv("SERVER_WALLET_ADDRESS", "0x255F9991233f86B29dB847c8d5b8CB9915e80dCf")

# Multi-chain configurations & deployed contracts
NETWORKS = {
    "polygon": {
        "chainId": 137,
        "name": "Polygon Mainnet",
        "explorer": "https://polygonscan.com",
        "api_url": "https://api.polygonscan.com/api",
        "api_key_env": "POLYGONSCAN_API_KEY",
        "usdc": "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359",
        "contracts": {
            "SafeSecurityGateGuard": "0x5cC5Afa2a97599d492A3E408Fdd95fD0b520f173",
            "AgentCreditOracle": "0x6418f408cFf03F862D7691f01fAb00a895E6aB93",
            "AgentComplianceRegistry": "0x28292D76E07E5539F15F3b97935dE8E0432E76DD",
            "AgentEscrow": "0x8ACafCEce0B1BFE140e75614b90FD1307b6f389d",
            "AgentLendingPool": "0xe43a9C368808B2dfF139D27789C40A3C8F2282cF",
            "AgentInsurancePool": "0xE67F4BC75B11dBb3ef2C9Ad1848B4b193c2c69C6",
            "AgentFactoringPool": "0xd0Aa4Aed2AeDE14611B53C3e93CF784F3Fe05BB0",
            "AgentTreasuryVault": "0xfCf3BF5fB5858db9aE81bE458B39b0032fc0C638",
            "SecurityGateConsumer": "0x9E3dEE18D8139E1d20f9f7D1F6673c75727F1DDA"
        }
    },
    "base": {
        "chainId": 8453,
        "name": "Base Mainnet",
        "explorer": "https://basescan.org",
        "api_url": "https://api.basescan.org/api",
        "api_key_env": "BASESCAN_API_KEY",
        "usdc": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        "contracts": {
            "SecurityGateConsumer": "0xdC6Cb774d51681Fcbba0E67Ca677dEc5705aaB35"
        }
    },
    "arbitrum": {
        "chainId": 42161,
        "name": "Arbitrum One",
        "explorer": "https://arbiscan.io",
        "api_url": "https://api.arbiscan.io/api",
        "api_key_env": "ARBISCAN_API_KEY",
        "usdc": "0xaf88d065e77c8cC2239327C5EDb3A432268e5831",
        "contracts": {
            "SecurityGateConsumer": "0xdC6Cb774d51681Fcbba0E67Ca677dEc5705aaB35"
        }
    }
}


def get_constructor_args(contract_name: str, chain: str) -> str:
    """Encodes constructor arguments into hex string."""
    net = NETWORKS[chain]
    usdc = net["usdc"]

    if contract_name == "SafeSecurityGateGuard":
        # constructor(address _oracleSigner, uint8 _maxAllowedRiskScore)
        encoded = encode(["address", "uint8"], [ORACLE_SIGNER, 30])
        return encoded.hex()
    elif contract_name in ["AgentCreditOracle", "SecurityGateConsumer"]:
        # constructor(address _oracleSigner)
        encoded = encode(["address"], [ORACLE_SIGNER])
        return encoded.hex()
    elif contract_name == "AgentComplianceRegistry":
        # constructor(address _complianceOracleSigner)
        encoded = encode(["address"], [ORACLE_SIGNER])
        return encoded.hex()
    elif contract_name == "AgentEscrow":
        # constructor(address _paymentToken, address _oracleSigner)
        encoded = encode(["address", "address"], [usdc, ORACLE_SIGNER])
        return encoded.hex()
    elif contract_name == "AgentLendingPool":
        # constructor(address _usdcToken, address _creditOracle)
        credit_oracle = net["contracts"].get("AgentCreditOracle", "0x6418f408cFf03F862D7691f01fAb00a895E6aB93")
        encoded = encode(["address", "address"], [usdc, credit_oracle])
        return encoded.hex()
    elif contract_name in ["AgentInsurancePool", "AgentFactoringPool", "AgentTreasuryVault"]:
        # constructor(address _usdcToken, address _oracleSigner, address _oracleTreasury)
        encoded = encode(["address", "address", "address"], [usdc, ORACLE_SIGNER, TREASURY])
        return encoded.hex()
    else:
        raise ValueError(f"Unknown contract {contract_name}")


def display_verification_details(chain: str):
    """Outputs structured verification parameters and direct URLs."""
    net = NETWORKS[chain]
    print(f"\n========================================================")
    print(f"  VERIFICATION PARAMETERS: {net['name']} (Chain ID {net['chainId']})")
    print(f"========================================================")
    print(f"Compiler Version:  v0.8.20+commit.a1b79de6")
    print(f"Optimization:      {'No' if chain == 'polygon' else 'Enabled (200 runs)'}")
    print(f"License:           MIT License")
    print(f"Oracle / Signer:   {ORACLE_SIGNER}")
    print(f"Native USDC:       {net['usdc']}")

    for cname, address in net["contracts"].items():
        c_args = get_constructor_args(cname, chain)
        source_file = VERIFICATION_DIR / f"{cname}.flattened.sol"
        verify_url = f"{net['explorer']}/verifyContract?a={address}"
        
        print(f"\n--- [{cname}] ---")
        print(f"Contract Address:  {address}")
        print(f"Direct Verify URL: {verify_url}")
        print(f"Flattened Source:  {source_file}")
        print(f"Constructor Hex:   {c_args}")


def main():
    parser = argparse.ArgumentParser(description="Contract Verification Helper for Security Gate x402")
    parser.add_argument("--chain", choices=["polygon", "base", "arbitrum", "all"], default="polygon")
    args = parser.parse_args()

    chains = ["polygon", "base", "arbitrum"] if args.chain == "all" else [args.chain]
    for c in chains:
        display_verification_details(c)


if __name__ == "__main__":
    main()
