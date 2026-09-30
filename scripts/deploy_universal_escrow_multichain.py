"""
Multi-Chain Deployment Script for UniversalEscrowCore.sol & ITruthAdapter.sol.
Deploys and registers on:
1. Polygon Mainnet (137)
2. Base Mainnet (8453)
3. Arbitrum One (42161)

Usage:
    python scripts/deploy_universal_escrow_multichain.py --chain polygon
    python scripts/deploy_universal_escrow_multichain.py --chain base
    python scripts/deploy_universal_escrow_multichain.py --chain arbitrum
    python scripts/deploy_universal_escrow_multichain.py --all
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

DEPLOYMENT_RECORD_FILE = Path("deployed_universal_escrow_multichain.json")

CHAIN_CONFIGS = {
    "polygon": {
        "name": "Polygon Mainnet",
        "chain_id": 137,
        "symbol": "POL",
        "min_balance": 0.05,
        "explorer": "https://polygonscan.com",
        "rpcs": [
            "https://polygon-rpc.com",
            "https://polygon-bor-rpc.publicnode.com",
            "https://1rpc.io/matic"
        ]
    },
    "base": {
        "name": "Base Mainnet",
        "chain_id": 8453,
        "symbol": "ETH",
        "min_balance": 0.0001,
        "explorer": "https://basescan.org",
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
        "min_balance": 0.0001,
        "explorer": "https://arbiscan.io",
        "rpcs": [
            "https://arb1.arbitrum.io/rpc",
            "https://arbitrum.llamarpc.com",
            "https://1rpc.io/arb"
        ]
    }
}


def compile_universal_contracts():
    """Compiles UniversalEscrowCore.sol and ITruthAdapter.sol using solc standard JSON via-IR."""
    print("\n📦 Compiling UniversalEscrowCore.sol and ITruthAdapter.sol with solc 0.8.20 (via-IR)...")
    solcx.install_solc("0.8.20")
    
    standard_input = {
        "language": "Solidity",
        "sources": {
            "UniversalEscrowCore.sol": {"urls": ["contracts/UniversalEscrowCore.sol"]},
            "ITruthAdapter.sol": {"urls": ["contracts/ITruthAdapter.sol"]},
            "TruthAdapter.sol": {"urls": ["contracts/TruthAdapter.sol"]}
        },
        "settings": {
            "optimizer": {"enabled": True, "runs": 200},
            "viaIR": True,
            "outputSelection": {"*": {"*": ["abi", "evm.bytecode"]}}
        }
    }
    compiled = solcx.compile_standard(standard_input, solc_version="0.8.20", allow_paths=["contracts"])
    
    core_abi = compiled["contracts"]["UniversalEscrowCore.sol"]["UniversalEscrowCore"]["abi"]
    core_bin = compiled["contracts"]["UniversalEscrowCore.sol"]["UniversalEscrowCore"]["evm"]["bytecode"]["object"]

    adapter_abi = compiled["contracts"]["TruthAdapter.sol"]["TruthAdapter"]["abi"]
    adapter_bin = compiled["contracts"]["TruthAdapter.sol"]["TruthAdapter"]["evm"]["bytecode"]["object"]

    print("✅ Contracts compiled successfully!")
    return {
        "UniversalEscrowCore": {"abi": core_abi, "bin": core_bin},
        "TruthAdapter": {"abi": adapter_abi, "bin": adapter_bin}
    }


def connect_rpc(chain_key: str):
    from web3.middleware import ExtraDataToPOAMiddleware
    config = CHAIN_CONFIGS[chain_key]
    for rpc in config["rpcs"]:
        try:
            w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={"timeout": 15}))
            if chain_key == "polygon":
                w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
            if w3.is_connected():
                print(f"🔗 Connected to {config['name']} via {rpc} (Block: {w3.eth.block_number})")
                return w3
        except Exception as e:
            print(f"   [WARN] RPC {rpc} failed: {e}. Trying fallback...")
    raise ConnectionError(f"Failed to connect to any RPC for {chain_key}")


def send_tx_robust(w3: Web3, account: Account, tx_dict: dict, chain_key: str):
    """Signs, broadcasts, and waits for transaction receipt with EIP-1559 support and retry backoff."""
    tx_params = dict(tx_dict)
    tx_params["from"] = account.address
    tx_params["chainId"] = CHAIN_CONFIGS[chain_key]["chain_id"]
    
    if "nonce" not in tx_params:
        tx_params["nonce"] = w3.eth.get_transaction_count(account.address, "pending")

    gas_price = w3.eth.gas_price
    try:
        fee_hist = w3.eth.fee_history(1, "latest", [50])
        base_fee = fee_hist["baseFeePerGas"][-1]
        priority_fee = w3.to_wei(0.001, "gwei") if chain_key in ("base", "arbitrum") else w3.to_wei(35, "gwei")
        tx_params["maxFeePerGas"] = int(base_fee * 1.5) + priority_fee
        tx_params["maxPriorityFeePerGas"] = priority_fee
    except Exception:
        tx_params["gasPrice"] = max(int(gas_price * 1.3), 35000000000 if chain_key == "polygon" else gas_price)

    if "gas" not in tx_params:
        estimated = w3.eth.estimate_gas(tx_params)
        tx_params["gas"] = int(estimated * 1.35)

    tx_hash = None
    for attempt in range(5):
        try:
            signed = account.sign_transaction(tx_params)
            tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
            break
        except Exception as e:
            err_str = str(e)
            if "in-flight" in err_str or "already known" in err_str or "nonce" in err_str or "-32000" in err_str:
                print(f"   [WARN] RPC busy (attempt {attempt+1}/5): {err_str[:70]}... waiting 5s")
                time.sleep(5)
                tx_params["nonce"] = w3.eth.get_transaction_count(account.address, "pending")
            else:
                raise

    print(f"   🚀 Sent Tx: {tx_hash.hex()} ... waiting for confirmation")
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
    if receipt.status != 1:
        raise RuntimeError(f"Transaction failed on-chain: {tx_hash.hex()}")
    print(f"   ✅ Confirmed in block {receipt.blockNumber} (Gas used: {receipt.gasUsed:,})")
    time.sleep(3)  # Mempool sync grace period
    return receipt


def deploy_chain(chain_key: str, compiled_artifacts: dict, existing_records: dict = None):
    config = CHAIN_CONFIGS[chain_key]
    print("\n" + "═" * 78)
    print(f"🏛️  DEPLOYING UNIVERSAL ESCROW CORE & TRUTH ADAPTER TO {config['name'].upper()}")
    print("═" * 78)

    w3 = connect_rpc(chain_key)
    deployer_pk = os.getenv("DEPLOYER_PRIVATE_KEY") or os.getenv("GATE_PRIVATE_KEY")
    if not deployer_pk:
        raise ValueError("Missing DEPLOYER_PRIVATE_KEY in .env")
    account = Account.from_key(deployer_pk.strip().strip('"').strip("'"))
    
    bal = w3.eth.get_balance(account.address)
    bal_eth = float(w3.from_wei(bal, "ether"))
    print(f"👛 Deployer Address: {account.address}")
    print(f"💰 Balance: {bal_eth:.6f} {config['symbol']}")
    if bal_eth < config["min_balance"]:
        raise ValueError(f"Insufficient balance ({bal_eth} < {config['min_balance']})")

    oracle_signer = os.getenv("SERVER_WALLET_ADDRESS") or account.address
    treasury = account.address  # A.GRID Treasury
    print(f"🛡️ Oracle Signer: {oracle_signer}")
    print(f"🏛️ Treasury: {treasury}")

    adapter_data = compiled_artifacts["TruthAdapter"]
    core_data = compiled_artifacts["UniversalEscrowCore"]

    # Check if already deployed on this chain (e.g. Polygon resuming)
    adapter_address = None
    rc_adapter_tx = None
    core_address = None
    rc_core_tx = None

    if chain_key == "polygon":
        # Check known live polygon addresses
        known_adapter = "0xCDE0edBE56Ae24D99F57eDacFB860a8c76f0856e"
        known_core = "0x4Dbd77F4799816859a595f24a57A786516D2EAa8"
        if len(w3.eth.get_code(known_adapter)) > 0 and len(w3.eth.get_code(known_core)) > 0:
            print("⚡ Found already deployed contracts on Polygon:")
            print(f"   • TruthAdapter: {known_adapter}")
            print(f"   • UniversalEscrowCore: {known_core}")
            adapter_address = known_adapter
            core_address = known_core
            rc_adapter_tx = "e4dc3edb5b0625f2fcd7a864202a8227e43ae34a19c053e805f926ec7c27c136"
            rc_core_tx = "9fd5a4a280ea691db511c33c4b4c6d85e94824345472027f634de1c4fc43349e"

    # =========================================================================
    # 1. Deploy TruthAdapter (if not already deployed)
    # =========================================================================
    if not adapter_address:
        print(f"\n[Step 1/3] Deploying TruthAdapter on {config['name']}...")
        adapter_contract = w3.eth.contract(abi=adapter_data["abi"], bytecode=adapter_data["bin"])
        adapter_deploy_tx = adapter_contract.constructor(oracle_signer, 0).build_transaction({"from": account.address})
        rc_adapter = send_tx_robust(w3, account, adapter_deploy_tx, chain_key)
        adapter_address = rc_adapter.contractAddress
        rc_adapter_tx = rc_adapter.transactionHash.hex()
        print(f"🎯 TruthAdapter Deployed: {adapter_address}")
        print(f"   Explorer: {config['explorer']}/address/{adapter_address}")

    # =========================================================================
    # 2. Deploy UniversalEscrowCore (if not already deployed)
    # =========================================================================
    if not core_address:
        print(f"\n[Step 2/3] Deploying UniversalEscrowCore on {config['name']}...")
        core_contract = w3.eth.contract(abi=core_data["abi"], bytecode=core_data["bin"])
        core_deploy_tx = core_contract.constructor(oracle_signer, treasury).build_transaction({"from": account.address})
        rc_core = send_tx_robust(w3, account, core_deploy_tx, chain_key)
        core_address = rc_core.contractAddress
        rc_core_tx = rc_core.transactionHash.hex()
        print(f"🎯 UniversalEscrowCore Deployed: {core_address}")
        print(f"   Explorer: {config['explorer']}/address/{core_address}")

    # =========================================================================
    # 3. Register Domain Adapters on UniversalEscrowCore
    # =========================================================================
    print(f"\n[Step 3/3] Registering TruthAdapter on UniversalEscrowCore domains (0, 1, 2)...")
    live_core = w3.eth.contract(address=core_address, abi=core_data["abi"])
    
    registration_txs = []
    for domain_id in (0, 1, 2):
        current_adapter = live_core.functions.domainAdapters(domain_id).call()
        if current_adapter.lower() == adapter_address.lower():
            print(f"   Domain {domain_id} already registered to {adapter_address} - skipping.")
            continue
        print(f"   Registering domain {domain_id} -> {adapter_address}...")
        set_adapter_tx = live_core.functions.setDomainAdapter(domain_id, adapter_address).build_transaction({"from": account.address})
        rc_set = send_tx_robust(w3, account, set_adapter_tx, chain_key)
        registration_txs.append(rc_set.transactionHash.hex())

    print("✅ All Domain Truth Adapters Registered on-chain!")

    record = {
        "chain_id": config["chain_id"],
        "network": config["name"],
        "deployer": account.address,
        "oracle_signer": oracle_signer,
        "treasury": treasury,
        "universal_escrow_core": core_address,
        "universal_escrow_core_deploy_tx": rc_core_tx,
        "truth_adapter": adapter_address,
        "truth_adapter_deploy_tx": rc_adapter_tx,
        "adapter_registration_txs": registration_txs,
        "deployed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }
    return record



def main():
    parser = argparse.ArgumentParser(description="Deploy UniversalEscrowCore and TruthAdapter across Polygon, Base, Arbitrum.")
    parser.add_argument("--chain", choices=["polygon", "base", "arbitrum"], help="Target chain key")
    parser.add_argument("--all", action="store_true", help="Deploy sequentially across all 3 chains")
    args = parser.parse_args()

    if not args.chain and not args.all:
        args.all = True

    compiled = compile_universal_contracts()

    existing_records = {}
    if DEPLOYMENT_RECORD_FILE.exists():
        try:
            with open(DEPLOYMENT_RECORD_FILE, "r", encoding="utf-8") as f:
                existing_records = json.load(f)
        except Exception:
            existing_records = {}

    target_chains = ["polygon", "base", "arbitrum"] if args.all else [args.chain]

    for c in target_chains:
        record = deploy_chain(c, compiled)
        existing_records[c] = record
        with open(DEPLOYMENT_RECORD_FILE, "w", encoding="utf-8") as f:
            json.dump(existing_records, f, indent=2)
        print(f"💾 Updated {DEPLOYMENT_RECORD_FILE} for {c}")

    print("\n" + "═" * 78)
    print("🎉 MULTI-CHAIN DEPLOYMENT SUMMARY")
    print("═" * 78)
    for c, r in existing_records.items():
        print(f"• {r['network']} (Chain ID {r['chain_id']}):")
        print(f"  - UniversalEscrowCore: {r['universal_escrow_core']}")
        print(f"  - TruthAdapter:       {r['truth_adapter']}")
    print("═" * 78 + "\n")


if __name__ == "__main__":
    main()
