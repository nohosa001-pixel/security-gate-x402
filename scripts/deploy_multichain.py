"""
Unified Multi-Chain Deployment & Verification Script for SecurityGateConsumer.sol.
Supports Polygon Mainnet (137), Base Mainnet (8453), Arbitrum One (42161),
Base Sepolia Testnet (84532), Arbitrum Sepolia Testnet (421614), and Polygon Amoy (80002).

Usage:
    python scripts/deploy_multichain.py --chain base
    python scripts/deploy_multichain.py --chain arbitrum
    python scripts/deploy_multichain.py --chain polygon
    python scripts/deploy_multichain.py --chain base-sepolia
"""

import os
import sys
import json
import time
import argparse
from pathlib import Path
import solcx
from web3 import Web3
from eth_account import Account
from dotenv import load_dotenv

load_dotenv()

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Multi-chain network configurations & RPC fallbacks
CHAIN_CONFIGS = {
    "polygon": {
        "name": "Polygon Mainnet",
        "chain_id": 137,
        "symbol": "POL",
        "min_balance": 0.05,
        "rpcs": [
            "https://polygon-rpc.com",
            "https://1rpc.io/matic",
            "https://polygon-bor-rpc.publicnode.com"
        ]
    },
    "base": {
        "name": "Base Mainnet",
        "chain_id": 8453,
        "symbol": "ETH",
        "min_balance": 0.0003,  # ~$1 worth of ETH
        "rpcs": [
            "https://mainnet.base.org",
            "https://base.llamarpc.com",
            "https://1rpc.io/base"
        ]
    },
    "arbitrum": {
        "name": "Arbitrum One",
        "chain_id": 42161,
        "symbol": "ETH",
        "min_balance": 0.0003,
        "rpcs": [
            "https://arb1.arbitrum.io/rpc",
            "https://arbitrum.llamarpc.com",
            "https://1rpc.io/arb"
        ]
    },
    "base-sepolia": {
        "name": "Base Sepolia Testnet",
        "chain_id": 84532,
        "symbol": "ETH",
        "min_balance": 0.0001,
        "rpcs": [
            "https://sepolia.base.org",
            "https://base-sepolia-rpc.publicnode.com"
        ]
    },
    "arbitrum-sepolia": {
        "name": "Arbitrum Sepolia Testnet",
        "chain_id": 421614,
        "symbol": "ETH",
        "min_balance": 0.0001,
        "rpcs": [
            "https://sepolia-rollup.arbitrum.io/rpc",
            "https://arbitrum-sepolia.blockpi.network/v1/rpc/public"
        ]
    },
    "amoy": {
        "name": "Polygon Amoy Testnet",
        "chain_id": 80002,
        "symbol": "POL",
        "min_balance": 0.05,
        "rpcs": [
            "https://rpc-amoy.polygon.technology"
        ]
    }
}


def get_web3_for_chain(chain_key: str):
    config = CHAIN_CONFIGS.get(chain_key)
    if not config:
        raise ValueError(f"Unsupported chain: {chain_key}. Choose from {list(CHAIN_CONFIGS.keys())}")

    for rpc in config["rpcs"]:
        try:
            w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={"timeout": 12}))
            if w3.is_connected():
                return w3, rpc, config
        except Exception:
            continue
    raise ConnectionError(f"Failed to connect to any RPC endpoint for {config['name']}")


def deploy_and_verify(chain_key: str, custom_oracle_signer: str = None):
    print("=" * 80)
    print(f"🚀 [MULTI-CHAIN DEPLOYMENT] Target: {chain_key.upper()}")
    print("=" * 80)

    w3, active_rpc, config = get_web3_for_chain(chain_key)
    chain_id = config["chain_id"]
    symbol = config["symbol"]
    print(f"✅ Connected to {config['name']} via {active_rpc} (Chain ID: {chain_id})")

    deployer_pk = os.getenv("DEPLOYER_PRIVATE_KEY") or os.getenv("GATE_PRIVATE_KEY")
    if not deployer_pk:
        print("[ERROR] Missing DEPLOYER_PRIVATE_KEY or GATE_PRIVATE_KEY in .env.")
        print("        You can copy your MetaMask private key into .env: DEPLOYER_PRIVATE_KEY=0x...")
        sys.exit(1)

    deployer_pk = deployer_pk.strip().strip('"').strip("'")
    if not deployer_pk.startswith("0x"):
        deployer_pk = "0x" + deployer_pk

    account = Account.from_key(deployer_pk)
    balance_wei = w3.eth.get_balance(account.address)
    balance_native = balance_wei / 1e18

    print(f"👛 Deployer Wallet: {account.address}")
    print(f"💰 Available Balance: {balance_native:.6f} {symbol}")

    if balance_native < config["min_balance"]:
        print(f"[ERROR] Insufficient balance. Need at least {config['min_balance']} {symbol} for deployment gas.")
        sys.exit(1)

    oracle_signer = custom_oracle_signer or os.getenv("SERVER_WALLET_ADDRESS") or account.address
    print(f"🛡️ Oracle Signer Address: {oracle_signer}")

    # 1. Compile SecurityGateConsumer.sol
    contract_file = Path("contracts/SecurityGateConsumer.sol")
    if not contract_file.exists():
        print(f"[ERROR] Contract file {contract_file} not found.")
        sys.exit(1)

    print("\n📦 Compiling SecurityGateConsumer.sol (v0.8.20 with via-IR optimizer)...")
    solcx.install_solc("0.8.20")
    compiled = solcx.compile_files(
        [str(contract_file)],
        solc_version="0.8.20",
        via_ir=True,
        optimize=True,
        optimize_runs=200,
        output_values=["abi", "bin"]
    )

    # Find compiled contract data regardless of OS path separators
    contract_data = None
    for k, v in compiled.items():
        if k.endswith("SecurityGateConsumer.sol:SecurityGateConsumer") or k.endswith(":SecurityGateConsumer"):
            contract_data = v
            break

    if not contract_data:
        raise KeyError(f"SecurityGateConsumer not found in compiled outputs: {list(compiled.keys())}")

    abi = contract_data["abi"]
    bytecode = contract_data["bin"]
    print("✅ Contract compiled successfully!")

    # 2. Build deployment transaction
    contract = w3.eth.contract(abi=abi, bytecode=bytecode)
    current_nonce = w3.eth.get_transaction_count(account.address)
    gas_price = w3.eth.gas_price

    # EIP-1559 or legacy gas pricing
    tx_params = {
        "from": account.address,
        "nonce": current_nonce,
        "chainId": chain_id
    }

    try:
        # Check if EIP-1559 fee history available
        fee_history = w3.eth.fee_history(1, "latest", [50])
        base_fee = fee_history["baseFeePerGas"][-1]
        priority_fee = w3.to_wei(0.001, "gwei") if chain_key in ("base", "arbitrum") else w3.to_wei(30, "gwei")
        tx_params["maxFeePerGas"] = int(base_fee * 1.5) + priority_fee
        tx_params["maxPriorityFeePerGas"] = priority_fee
    except Exception:
        tx_params["gasPrice"] = max(int(gas_price * 1.25), 35000000000 if chain_key == "polygon" else gas_price)

    tx = contract.constructor(oracle_signer).build_transaction(tx_params)
    estimated_gas = w3.eth.estimate_gas(tx)
    tx["gas"] = int(estimated_gas * 1.2)

    print(f"\n📡 Broadcasting deployment tx to {config['name']}...")
    signed_tx = w3.eth.account.sign_transaction(tx, private_key=deployer_pk)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    print(f"Transaction Hash: {tx_hash.hex()}")
    print("⏳ Waiting for transaction receipt...")

    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
    contract_address = receipt.contractAddress
    print(f"\n🎉 Deployment Confirmed in block #{receipt.blockNumber}!")
    print(f"📍 Contract Address: {contract_address}")
    print(f"⛽ Gas Used: {receipt.gasUsed:,}")

    # Wait 3 seconds for RPC node synchronization
    time.sleep(3)

    # 3. Verify on-chain contract getters
    deployed_contract = w3.eth.contract(address=contract_address, abi=abi)
    onchain_oracle = deployed_contract.functions.oracleSigner().call()
    onchain_owner = deployed_contract.functions.owner().call()
    domain_sep = deployed_contract.functions.DOMAIN_SEPARATOR().call()

    print("\n🔍 On-Chain Getter Verification:")
    print(f"  • oracleSigner:     {onchain_oracle}")
    print(f"  • owner:            {onchain_owner}")
    print(f"  • DOMAIN_SEPARATOR: {domain_sep.hex()}")

    assert onchain_oracle.lower() == oracle_signer.lower(), "Oracle Signer mismatch!"
    assert onchain_owner.lower() == account.address.lower(), "Owner mismatch!"

    # 4. Save metadata to deployed_contracts_{chain_key}.json
    record = {
        "network": config["name"],
        "chain_id": chain_id,
        "contract_name": "SecurityGateConsumer",
        "contract_address": contract_address,
        "oracle_signer": onchain_oracle,
        "deployer_address": account.address,
        "transaction_hash": tx_hash.hex(),
        "block_number": receipt.blockNumber,
        "deployed_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "abi": abi
    }

    out_file = Path(f"deployed_contracts_{chain_key}.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2)

    print(f"💾 Saved deployment artifact to: {out_file.name}")
    print("\n✨ [SUCCESS] Ready to protect autonomous agent transactions on " + config["name"] + "!")
    return record


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Multi-chain deployment script for SecurityGateConsumer.sol")
    parser.add_argument(
        "--chain",
        type=str,
        default="polygon",
        choices=list(CHAIN_CONFIGS.keys()),
        help="Target blockchain network (e.g. polygon, base, arbitrum, base-sepolia, arbitrum-sepolia, amoy)"
    )
    parser.add_argument(
        "--oracle-signer",
        type=str,
        default=None,
        help="Custom oracle signer address (defaults to SERVER_WALLET_ADDRESS or deployer)"
    )
    args = parser.parse_args()
    deploy_and_verify(args.chain, args.oracle_signer)
