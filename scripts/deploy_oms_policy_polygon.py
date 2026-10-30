#!/usr/bin/env python3
"""
Polygon Mainnet Deployment & Registration Script for SecurityGateOMSPolicy.sol:
1. Loads compiled ABI/Bytecode from contracts/abi/SecurityGateOMSPolicy.json.
2. Deploys to Polygon Mainnet (Chain ID 137).
3. Verifies on-chain getters: oracleSigner(), owner(), DOMAIN_SEPARATOR(), maxAllowedRiskScore().
4. Registers and updates deployed_contracts_polygon.json.
"""

import os
import sys
import json
import time
from pathlib import Path
from web3 import Web3
from eth_account import Account
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

RPC_ENDPOINTS = [
    os.getenv("POLYGON_RPC_URL", "https://polygon-rpc.com"),
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
    raise ConnectionError("Failed to connect to Polygon Mainnet RPC.")


def main():
    print("=" * 80)
    print("🚀 [DEPLOYING & REGISTERING SecurityGateOMSPolicy.sol ON POLYGON MAINNET (137)]")
    print("=" * 80)

    w3, rpc = get_web3()
    print(f"Connected to Polygon Mainnet via {rpc} (Chain ID: {w3.eth.chain_id})")

    deployer_pk = os.getenv("DEPLOYER_PRIVATE_KEY") or os.getenv("GATE_PRIVATE_KEY")
    if not deployer_pk:
        bot_wallet_path = ROOT_DIR / "data" / "bot_wallet_evm.json"
        if bot_wallet_path.exists():
            try:
                bot_data = json.loads(bot_wallet_path.read_text(encoding="utf-8"))
                deployer_pk = bot_data.get("private_key")
                print(f"[*] Loaded active bot wallet from {bot_wallet_path.name}")
            except Exception:
                pass

    if not deployer_pk:
        print("[ERROR] Missing DEPLOYER_PRIVATE_KEY or GATE_PRIVATE_KEY in .env and data/bot_wallet_evm.json.")
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
        print(f"[ERROR] Insufficient balance ({balance_pol:.4f} POL). Need at least 0.05 POL.")
        sys.exit(1)

    oracle_signer = os.getenv("SERVER_WALLET_ADDRESS") or "0xA185B43fDD19619f99952AAed6eabf1029bF36a1"
    print(f"Oracle Signer Address: {oracle_signer}")

    # 1. Load compiled artifact
    artifact_path = ROOT_DIR / "contracts" / "abi" / "SecurityGateOMSPolicy.json"
    if not artifact_path.exists():
        print("[ERROR] Compiled artifact not found at contracts/abi/SecurityGateOMSPolicy.json")
        sys.exit(1)

    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    abi = artifact["abi"]
    bytecode = artifact["bytecode"]
    if not bytecode.startswith("0x"):
        bytecode = "0x" + bytecode
    print("✅ Contract artifact loaded successfully!")

    # 2. Build deployment transaction
    contract = w3.eth.contract(abi=abi, bytecode=bytecode)
    current_nonce = w3.eth.get_transaction_count(account.address)
    network_gas_price = w3.eth.gas_price
    gas_price = max(int(network_gas_price * 1.25), 35000000000)  # Min 35 Gwei on Polygon

    tx = contract.constructor(oracle_signer).build_transaction({
        "from": account.address,
        "nonce": current_nonce,
        "gasPrice": gas_price,
        "chainId": 137
    })

    try:
        estimated_gas = w3.eth.estimate_gas(tx)
        tx["gas"] = min(int(estimated_gas * 1.2), 1500000)
    except Exception as e:
        print(f"[!] Gas estimate warning: {e}. Defaulting to 1,200,000 gas limit.")
        tx["gas"] = 1200000

    print(f"Gas Limit: {tx['gas']:,}, Gas Price: {gas_price / 1e9:.2f} Gwei")

    # 3. Broadcast deployment transaction
    print("\n[*] Signing and broadcasting transaction...")
    signed_tx = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    print(f"📡 Broadcast TX: https://polygonscan.com/tx/{tx_hash.hex()}")
    print("⏳ Waiting for block confirmation on Polygon...")

    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
    if receipt.status != 1:
        print(f"[ERROR] Deployment transaction reverted! Status: {receipt.status}")
        sys.exit(1)

    deployed_address = receipt.contractAddress
    print(f"\n🎉 [SUCCESS] SecurityGateOMSPolicy DEPLOYED AT: {deployed_address}")
    print(f"   Block Number: {receipt.blockNumber}")
    print(f"   Gas Used:     {receipt.gasUsed:,}")

    # 4. On-Chain Verification of Getters
    print("\n🔍 Verifying On-Chain Contract State...")
    deployed_contract = w3.eth.contract(address=deployed_address, abi=abi)

    onchain_oracle = deployed_contract.functions.oracleSigner().call()
    onchain_owner = deployed_contract.functions.owner().call()
    onchain_risk = deployed_contract.functions.maxAllowedRiskScore().call()
    domain_separator = deployed_contract.functions.DOMAIN_SEPARATOR().call()
    escrow_hub = deployed_contract.functions.DEFAULT_POLYGON_ESCROW_HUB().call()

    print(f"   - On-chain oracleSigner():          {onchain_oracle}")
    print(f"   - On-chain owner():                 {onchain_owner}")
    print(f"   - On-chain maxAllowedRiskScore():   {onchain_risk}")
    print(f"   - DEFAULT_POLYGON_ESCROW_HUB:       {escrow_hub}")
    print(f"   - DOMAIN_SEPARATOR:                 {domain_separator.hex()}")

    assert onchain_oracle.lower() == oracle_signer.lower(), "Oracle signer mismatch!"
    assert onchain_owner.lower() == oracle_signer.lower(), "Owner mismatch! Owner must be Oracle Signer."
    print("✅ On-chain getters verified 100% correctly! (Owner == Oracle Signer)")

    # 5. Update deployed_contracts_polygon.json
    state_file = ROOT_DIR / "deployed_contracts_polygon.json"
    state_data = {}
    if state_file.exists():
        try:
            with open(state_file, "r", encoding="utf-8") as f:
                state_data = json.load(f)
        except Exception:
            pass

    contracts_map = state_data.setdefault("contracts", {})
    contracts_map["SecurityGateOMSPolicy"] = deployed_address
    state_data["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    with open(state_file, "w", encoding="utf-8") as f:
        json.dump(state_data, f, indent=2)

    print(f"\n📝 Registered SecurityGateOMSPolicy in {state_file.name}: {deployed_address}")
    print("=" * 80)
    print(f"🚀 SecurityGateOMSPolicy.sol is LIVE on Polygon Mainnet!")
    print(f"   Address:     {deployed_address}")
    print(f"   PolygonScan: https://polygonscan.com/address/{deployed_address}")
    print("=" * 80)
    return deployed_address


if __name__ == "__main__":
    main()
