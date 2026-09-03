"""
Unified Multi-Chain Deployment Script for Agent Security Gate x402 Contracts.
Deploys SafeSecurityGateGuard, AgentCreditOracle, and AgentComplianceRegistry across:
- Polygon Mainnet (Chain ID: 137)
- Base Mainnet (Chain ID: 8453)
- Arbitrum One (Chain ID: 42161)
- Ethereum Mainnet (Chain ID: 1)
"""

import os
import sys
import json
import argparse
import solcx
from web3 import Web3
from eth_account import Account
from dotenv import load_dotenv

load_dotenv()

NETWORKS = {
    "polygon": {
        "name": "Polygon Mainnet",
        "chain_id": 137,
        "rpc_list": ["https://polygon-rpc.com", "https://1rpc.io/matic", "https://polygon-bor-rpc.publicnode.com"],
        "explorer": "https://polygonscan.com/address/"
    },
    "base": {
        "name": "Base Mainnet",
        "chain_id": 8453,
        "rpc_list": ["https://mainnet.base.org", "https://1rpc.io/base", "https://base.llamarpc.com"],
        "explorer": "https://basescan.org/address/"
    },
    "arbitrum": {
        "name": "Arbitrum One",
        "chain_id": 42161,
        "rpc_list": ["https://arb1.arbitrum.io/rpc", "https://1rpc.io/arb", "https://arbitrum.llamarpc.com"],
        "explorer": "https://arbiscan.io/address/"
    }
}


def get_web3_for_network(net_key: str):
    net = NETWORKS[net_key]
    for rpc in net["rpc_list"]:
        try:
            w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={"timeout": 15}))
            if w3.is_connected():
                return w3, rpc
        except Exception:
            continue
    raise ConnectionError(f"Failed to connect to any RPC for {net['name']}")


def deploy_network(net_key: str):
    net = NETWORKS[net_key]
    w3, active_rpc = get_web3_for_network(net_key)
    print(f"\n==================================================================")
    print(f"🚀 Deploying to {net['name']} (Chain ID: {net['chain_id']}) via {active_rpc}")
    print(f"==================================================================")

    pk = os.getenv("DEPLOYER_PRIVATE_KEY") or os.getenv("GATE_PRIVATE_KEY")
    if not pk:
        print("[ERROR] Missing DEPLOYER_PRIVATE_KEY in .env.")
        sys.exit(1)

    pk = pk.strip().strip('"').strip("'")
    if not pk.startswith("0x"):
        pk = "0x" + pk

    account = Account.from_key(pk)
    balance_eth = w3.eth.get_balance(account.address) / 1e18
    print(f"Deployer: {account.address}")
    print(f"Native Token Balance: {balance_eth:.6f}")

    if balance_eth < 0.001:
        print(f"[WARN] Balance on {net['name']} is very low ({balance_eth:.6f}). Transaction might revert.")

    oracle_signer = os.getenv("SERVER_WALLET_ADDRESS") or account.address
    print(f"Oracle Signer: {oracle_signer}")

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

    contracts = [
        ("SafeSecurityGateGuard", "contracts/SafeSecurityGateGuard.sol:SafeSecurityGateGuard", [oracle_signer, 30]),
        ("AgentCreditOracle", "contracts/AgentCreditOracle.sol:AgentCreditOracle", [oracle_signer]),
        ("AgentComplianceRegistry", "contracts/AgentComplianceRegistry.sol:AgentComplianceRegistry", [oracle_signer]),
    ]

    deployed = {}
    nonce = w3.eth.get_transaction_count(account.address)

    for name, contract_key, constructor_args in contracts:
        print(f"\nDeploying {name}...")
        c_data = compiled[contract_key]
        contract = w3.eth.contract(abi=c_data["abi"], bytecode=c_data["bin"])

        gas_price = int(w3.eth.gas_price * 1.3)
        if net["chain_id"] == 137:
            gas_price = max(gas_price, 35000000000)

        tx = contract.constructor(*constructor_args).build_transaction({
            "from": account.address,
            "nonce": nonce,
            "gasPrice": gas_price,
            "chainId": net["chain_id"]
        })

        gas_est = w3.eth.estimate_gas(tx)
        tx["gas"] = int(gas_est * 1.25)

        signed_tx = account.sign_transaction(tx)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        print(f"TxHash: {tx_hash.hex()}")

        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
        c_addr = receipt.contractAddress
        deployed[name] = c_addr
        print(f"✅ {name} LIVE at: {c_addr}")
        print(f"Explorer: {net['explorer']}{c_addr}")
        nonce += 1

    report_file = f"deployed_contracts_{net_key}.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump({
            "network": net["name"],
            "chain_id": net["chain_id"],
            "deployer": account.address,
            "contracts": deployed
        }, f, indent=2)
    print(f"\nSaved {report_file}!")


def main():
    parser = argparse.ArgumentParser(description="Multi-chain Contract Deployment")
    parser.add_argument("--chain", choices=["polygon", "base", "arbitrum", "all"], default="polygon")
    args = parser.parse_args()

    if args.chain == "all":
        for ch in ["polygon", "base", "arbitrum"]:
            deploy_network(ch)
    else:
        deploy_network(args.chain)


if __name__ == "__main__":
    main()
