"""
Polygon Mainnet Deployment Script for Agent Security Gate x402 Contracts:
1. SafeSecurityGateGuard.sol (Gnosis Safe Transaction Guard)
2. AgentCreditOracle.sol (Moody's & S&P Credit Rating Oracle)
3. AgentComplianceRegistry.sol (EU AI Act Compliance Registry)
"""

import os
import sys
import json
import solcx
from web3 import Web3
from eth_account import Account
from dotenv import load_dotenv

load_dotenv()

# High-reliability Polygon RPC endpoints
RPC_ENDPOINTS = [
    "https://polygon-rpc.com",
    "https://1rpc.io/matic",
    "https://polygon-bor-rpc.publicnode.com",
    "https://rpc.ankr.com/polygon"
]


def get_web3():
    for rpc in RPC_ENDPOINTS:
        try:
            w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={"timeout": 15}))
            if w3.is_connected():
                return w3, rpc
        except Exception:
            continue
    raise ConnectionError("Failed to connect to any Polygon Mainnet RPC endpoint.")


def deploy_all():
    w3, active_rpc = get_web3()
    print(f"Connected to Polygon Mainnet via {active_rpc} (Chain ID: {w3.eth.chain_id})")

    # Get deployer private key from environment
    deployer_pk = os.getenv("DEPLOYER_PRIVATE_KEY") or os.getenv("GATE_PRIVATE_KEY")
    if not deployer_pk:
        print("\n[ERROR] Missing 'DEPLOYER_PRIVATE_KEY' in .env file.")
        print("Please add your wallet private key to .env:")
        print("DEPLOYER_PRIVATE_KEY=0xYourPrivateKeyHere\n")
        sys.exit(1)

    deployer_pk = deployer_pk.strip().strip('"').strip("'")
    if not deployer_pk.startswith("0x"):
        deployer_pk = "0x" + deployer_pk

    account = Account.from_key(deployer_pk)
    balance_wei = w3.eth.get_balance(account.address)
    balance_matic = balance_wei / 1e18
    print(f"Deployer Wallet Address: {account.address}")
    print(f"Polygon POL/MATIC Balance: {balance_matic:.4f} POL")

    if balance_matic < 0.2:
        print("[ERROR] Insufficient balance. Need at least 0.2 POL to deploy contracts.")
        sys.exit(1)

    # Oracle Signer Address (Defaults to deployer address if not set)
    oracle_signer = os.getenv("SERVER_WALLET_ADDRESS") or account.address
    print(f"Setting Oracle Signer to: {oracle_signer}")

    # Compile contracts
    print("\nCompiling Solidity smart contracts (v0.8.20)...")
    solcx.install_solc("0.8.20")
    compiled = solcx.compile_files(
        [
            "contracts/SafeSecurityGateGuard.sol",
            "contracts/AgentCreditOracle.sol",
            "contracts/AgentComplianceRegistry.sol"
        ],
        solc_version="0.8.20",
        output_values=["abi", "bin"]
    )

    contracts_to_deploy = [
        ("SafeSecurityGateGuard", "contracts/SafeSecurityGateGuard.sol:SafeSecurityGateGuard", [oracle_signer, 30]),
        ("AgentCreditOracle", "contracts/AgentCreditOracle.sol:AgentCreditOracle", [oracle_signer]),
        ("AgentComplianceRegistry", "contracts/AgentComplianceRegistry.sol:AgentComplianceRegistry", [oracle_signer]),
    ]

    deployed_addresses = {}
    nonce = w3.eth.get_transaction_count(account.address)

    for name, contract_key, constructor_args in contracts_to_deploy:
        print(f"\n--- Deploying {name} to Polygon Mainnet ---")
        contract_data = compiled[contract_key]
        abi = contract_data["abi"]
        bytecode = contract_data["bin"]

        contract = w3.eth.contract(abi=abi, bytecode=bytecode)
        # Polygon mainnet min gas price is 30 Gwei
        network_gas_price = w3.eth.gas_price
        gas_price = max(int(network_gas_price * 1.3), 35000000000)

        tx = contract.constructor(*constructor_args).build_transaction({
            "from": account.address,
            "nonce": nonce,
            "gasPrice": gas_price,
            "chainId": 137
        })

        # Estimate gas
        gas_est = w3.eth.estimate_gas(tx)
        tx["gas"] = int(gas_est * 1.2)

        signed_tx = account.sign_transaction(tx)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        print(f"Transaction Broadcasted! TxHash: {tx_hash.hex()}")
        print("Waiting for block confirmation on Polygon...")

        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
        contract_address = receipt.contractAddress
        deployed_addresses[name] = contract_address
        print(f"[SUCCESS] {name} deployed at: {contract_address}")
        print(f"Polygonscan Explorer: https://polygonscan.com/address/{contract_address}")

        nonce += 1

    # Save deployment report
    report_path = "deployed_contracts_polygon.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump({
            "network": "Polygon Mainnet (Chain ID 137)",
            "deployer": account.address,
            "oracle_signer": oracle_signer,
            "contracts": deployed_addresses
        }, f, indent=2)

    print(f"\nSaved deployment report to {report_path}!")
    print("\nAll contracts are now LIVE on Polygon Mainnet!")


if __name__ == "__main__":
    deploy_all()
