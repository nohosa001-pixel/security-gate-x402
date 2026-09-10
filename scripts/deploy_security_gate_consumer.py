"""
Polygon Mainnet Deployment & Verification Script for SecurityGateConsumer.sol.
1. Compiles contracts/SecurityGateConsumer.sol with solc 0.8.20.
2. Deploys to Polygon Mainnet (Chain ID 137).
3. Verifies on-chain getters: oracleSigner(), owner(), DOMAIN_SEPARATOR().
4. Updates deployed_contracts_polygon.json.
"""

import os
import sys
import json
import time
from pathlib import Path
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
    print("🚀 [DEPLOYING & VERIFYING SecurityGateConsumer.sol ON POLYGON MAINNET]")
    print("=" * 80)

    w3, active_rpc = get_web3()
    print(f"Connected to Polygon Mainnet via {active_rpc} (Chain ID: {w3.eth.chain_id})")

    deployer_pk = os.getenv("DEPLOYER_PRIVATE_KEY") or os.getenv("GATE_PRIVATE_KEY")
    if not deployer_pk:
        print("[ERROR] Missing DEPLOYER_PRIVATE_KEY or GATE_PRIVATE_KEY in .env.")
        sys.exit(1)

    deployer_pk = deployer_pk.strip().strip('"').strip("'")
    if not deployer_pk.startswith("0x"):
        deployer_pk = "0x" + deployer_pk

    account = Account.from_key(deployer_pk)
    balance_wei = w3.eth.get_balance(account.address)
    balance_pol = balance_wei / 1e18

    print(f"Deployer Wallet: {account.address}")
    print(f"Available POL Balance: {balance_pol:.4f} POL")

    if balance_pol < 0.05:
        print("[ERROR] Insufficient balance. Need at least 0.05 POL.")
        sys.exit(1)

    oracle_signer = os.getenv("SERVER_WALLET_ADDRESS") or account.address
    print(f"Oracle Signer Address: {oracle_signer}")

    # 1. Compile SecurityGateConsumer.sol
    print("\n📦 Compiling SecurityGateConsumer.sol (v0.8.20 with via-IR optimizer)...")
    solcx.install_solc("0.8.20")
    compiled = solcx.compile_files(
        ["contracts/SecurityGateConsumer.sol"],
        solc_version="0.8.20",
        via_ir=True,
        optimize=True,
        optimize_runs=200,
        output_values=["abi", "bin"]
    )

    contract_key = "contracts/SecurityGateConsumer.sol:SecurityGateConsumer"
    contract_data = compiled[contract_key]
    abi = contract_data["abi"]
    bytecode = contract_data["bin"]
    print("✅ Contract compiled successfully!")

    # 2. Build deployment transaction
    contract = w3.eth.contract(abi=abi, bytecode=bytecode)
    current_nonce = w3.eth.get_transaction_count(account.address)
    network_gas_price = w3.eth.gas_price
    gas_price = max(int(network_gas_price * 1.2), 35000000000)  # 35 Gwei minimum on Polygon

    tx = contract.constructor(oracle_signer).build_transaction({
        "from": account.address,
        "nonce": current_nonce,
        "gasPrice": gas_price,
        "chainId": 137
    })

    try:
        estimated_gas = w3.eth.estimate_gas(tx)
        tx["gas"] = min(int(estimated_gas * 1.2), 1500000)
    except Exception:
        tx["gas"] = 1000000

    print(f"Gas Limit: {tx['gas']}, Gas Price: {gas_price / 1e9:.2f} Gwei")

    # 3. Broadcast deployment transaction
    signed_tx = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    print(f"📡 Broadcast TX: https://polygonscan.com/tx/{tx_hash.hex()}")
    print("⏳ Waiting for block confirmation on Polygon...")

    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
    deployed_address = receipt.contractAddress
    print(f"\n🎉 [SUCCESS] SecurityGateConsumer DEPLOYED AT: {deployed_address}")
    print(f"   Block Number: {receipt.blockNumber}")
    print(f"   Gas Used: {receipt.gasUsed}")

    # 4. On-Chain Verification of Getters
    print("\n🔍 Verifying On-Chain Contract State...")
    deployed_contract = w3.eth.contract(address=deployed_address, abi=abi)

    onchain_oracle = deployed_contract.functions.oracleSigner().call()
    onchain_owner = deployed_contract.functions.owner().call()
    domain_separator = deployed_contract.functions.DOMAIN_SEPARATOR().call()

    print(f"   - On-chain oracleSigner(): {onchain_oracle}")
    print(f"   - On-chain owner():        {onchain_owner}")
    print(f"   - DOMAIN_SEPARATOR:        {domain_separator.hex()}")

    assert onchain_oracle.lower() == oracle_signer.lower(), "Oracle signer mismatch!"
    assert onchain_owner.lower() == account.address.lower(), "Owner mismatch!"
    print("✅ On-chain getters verified 100% correctly!")

    # 5. Update deployed_contracts_polygon.json
    state_file = "deployed_contracts_polygon.json"
    state_data = {}
    if os.path.exists(state_file):
        try:
            with open(state_file, "r", encoding="utf-8") as f:
                state_data = json.load(f)
        except Exception:
            pass

    contracts_map = state_data.setdefault("contracts", {})
    contracts_map["SecurityGateConsumer"] = deployed_address
    state_data["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    with open(state_file, "w", encoding="utf-8") as f:
        json.dump(state_data, f, indent=2)

    print(f"📝 Updated {state_file} with SecurityGateConsumer: {deployed_address}")
    print("\n" + "=" * 80)
    print(f"🚀 SecurityGateConsumer.sol is LIVE on Polygon Mainnet!")
    print(f"   Address: {deployed_address}")
    print(f"   PolygonScan: https://polygonscan.com/address/{deployed_address}")
    print("=" * 80)


if __name__ == "__main__":
    main()
