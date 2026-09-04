"""
Polygon Mainnet Deployment Script for Stage 1-5 Autonomous AI Financial Metropolis:
1. AgentEscrow.sol (M2M Task Escrow & Slashing)
2. AgentLendingPool.sol (Uncollateralized Micro-Lending Pool)
3. AgentInsurancePool.sol (AI Malpractice & Liability Insurance)
4. AgentFactoringPool.sol (Receivables Factoring & Short-Term Bond Pool)
5. AgentTreasuryVault.sol (AI Agent Hedge Fund & Vault Manager)
"""

import os
import sys
import json
import time
import solcx
from web3 import Web3
from eth_account import Account
from dotenv import load_dotenv

load_dotenv()

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

RPC_ENDPOINTS = [
    "https://polygon-rpc.com",
    "https://1rpc.io/matic",
    "https://polygon-bor-rpc.publicnode.com",
    "https://rpc.ankr.com/polygon"
]

POLYGON_USDC_NATIVE = "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359"
DEPLOYED_CREDIT_ORACLE = "0x6418f408cFf03F862D7691f01fAb00a895E6aB93"


def get_web3():
    for rpc in RPC_ENDPOINTS:
        try:
            w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={"timeout": 15}))
            if w3.is_connected():
                return w3, rpc
        except Exception:
            continue
    raise ConnectionError("Failed to connect to any Polygon Mainnet RPC endpoint.")


def main():
    print("=" * 80)
    print("🚀 [DEPLOYING STAGE 1-5 AUTONOMOUS AGENT FINANCIAL PROTOCOLS TO POLYGON]")
    print("=" * 80)

    w3, active_rpc = get_web3()
    print(f"Connected to Polygon Mainnet via {active_rpc} (Chain ID: {w3.eth.chain_id})")

    deployer_pk = os.getenv("DEPLOYER_PRIVATE_KEY") or os.getenv("GATE_PRIVATE_KEY")
    if not deployer_pk:
        print("[ERROR] Missing DEPLOYER_PRIVATE_KEY in .env.")
        sys.exit(1)

    deployer_pk = deployer_pk.strip().strip('"').strip("'")
    if not deployer_pk.startswith("0x"):
        deployer_pk = "0x" + deployer_pk

    account = Account.from_key(deployer_pk)
    balance_wei = w3.eth.get_balance(account.address)
    balance_pol = balance_wei / 1e18

    print(f"Deployer Wallet: {account.address}")
    print(f"Available POL Balance: {balance_pol:.4f} POL")

    if balance_pol < 0.5:
        print("[ERROR] Need at least 0.5 POL to deploy 5 contracts.")
        sys.exit(1)

    oracle_signer = account.address
    oracle_treasury = account.address
    print(f"Oracle Signer Address:   {oracle_signer}")
    print(f"Oracle Treasury Address: {oracle_treasury}")

    # Compile Solidity Contracts
    print("\n📦 Compiling Solidity Smart Contracts (v0.8.20)...")
    solcx.install_solc("0.8.20")
    compiled = solcx.compile_files(
        [
            "contracts/AgentEscrow.sol",
            "contracts/AgentLendingPool.sol",
            "contracts/AgentInsurancePool.sol",
            "contracts/AgentFactoringPool.sol",
            "contracts/AgentTreasuryVault.sol"
        ],
        solc_version="0.8.20",
        output_values=["abi", "bin"]
    )

    contracts_to_deploy = [
        ("AgentInsurancePool", "contracts/AgentInsurancePool.sol:AgentInsurancePool", [POLYGON_USDC_NATIVE, oracle_signer, oracle_treasury]),
        ("AgentFactoringPool", "contracts/AgentFactoringPool.sol:AgentFactoringPool", [POLYGON_USDC_NATIVE, oracle_signer, oracle_treasury]),
        ("AgentTreasuryVault", "contracts/AgentTreasuryVault.sol:AgentTreasuryVault", [POLYGON_USDC_NATIVE, oracle_signer, oracle_treasury]),
    ]

    deployed_registry = {
        "AgentEscrow": "0x8ACafCEce0B1BFE140e75614b90FD1307b6f389d",
        "AgentLendingPool": "0xe43a9C368808B2dfF139D27789C40A3C8F2282cF",
    }
    print(f"Preserving already deployed: {deployed_registry}")
    current_nonce = w3.eth.get_transaction_count(account.address)

    for name, contract_key, constructor_args in contracts_to_deploy:
        print(f"\n--- Deploying {name} to Polygon Mainnet ---")
        c_data = compiled[contract_key]
        abi = c_data["abi"]
        bytecode = c_data["bin"]

        contract = w3.eth.contract(abi=abi, bytecode=bytecode)
        network_gas_price = w3.eth.gas_price
        gas_price = max(int(network_gas_price * 1.2), 35000000000)  # 35 Gwei min on Polygon

        tx = contract.constructor(*constructor_args).build_transaction({
            "from": account.address,
            "nonce": current_nonce,
            "gasPrice": gas_price,
            "chainId": 137
        })

        # Estimate gas with safe bounds
        try:
            estimated_gas = w3.eth.estimate_gas(tx)
            tx["gas"] = min(int(estimated_gas * 1.15), 2200000)
        except Exception:
            tx["gas"] = 2000000

        # Ensure max total tx fee doesn't exceed 0.8 POL cap of RPC nodes
        if tx["gas"] * gas_price > int(0.7 * 1e18):
            gas_price = int((0.7 * 1e18) / tx["gas"])
            tx["gasPrice"] = gas_price

        signed_tx = account.sign_transaction(tx)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        print(f"📡 Broadcast TX: https://polygonscan.com/tx/{tx_hash.hex()}")
        print("⏳ Waiting for block confirmation...")

        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
        contract_addr = receipt.contractAddress
        print(f"✅ {name} DEPLOYED AT: {contract_addr}")
        deployed_registry[name] = contract_addr

        current_nonce += 1
        time.sleep(2)

    # Save to deployed_contracts_polygon.json
    state_file = "deployed_contracts_polygon.json"
    existing_data = {}
    if os.path.exists(state_file):
        try:
            with open(state_file, "r") as f:
                existing_data = json.load(f)
        except Exception:
            pass

    existing_contracts = existing_data.get("contracts", {})
    existing_contracts.update(deployed_registry)

    updated_data = {
        "network": "Polygon Mainnet (Chain ID 137)",
        "deployer": account.address,
        "oracle_signer": oracle_signer,
        "oracle_treasury": oracle_treasury,
        "contracts": existing_contracts,
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }

    with open(state_file, "w") as f:
        json.dump(updated_data, f, indent=2)

    print("\n" + "=" * 80)
    print("🎉 [DEPLOYMENT SUCCESS] ALL 5 FINANCIAL PROTOCOLS LIVE ON POLYGON MAINNET!")
    for name, addr in deployed_registry.items():
        print(f"   - {name:20s}: https://polygonscan.com/address/{addr}")
    print("=" * 80)


if __name__ == "__main__":
    main()
