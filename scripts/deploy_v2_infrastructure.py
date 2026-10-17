"""
V2 Infrastructure Deployment & Orchestration Script
===================================================
Deploys and registers V2 smart contracts across EVM mainnets:
1. AgenticShieldPool.sol (ERC-4626 LP Underwriting & Autonomous Indemnification Vault)
2. LogisticsPoDEscrow.sol (B2B Proof-of-Delivery Autonomous Settlement Escrow)

Supported Networks:
- Base Mainnet (8453)
- Polygon Mainnet (137)
- Arbitrum One (42161)

Usage:
    python scripts/deploy_v2_infrastructure.py --chain base --dry-run
    python scripts/deploy_v2_infrastructure.py --chain base
    python scripts/deploy_v2_infrastructure.py --chain polygon
    python scripts/deploy_v2_infrastructure.py --all
"""

import os
import sys
import json
import time
import argparse
from pathlib import Path
from typing import Dict, Any, Tuple
from web3 import Web3
from eth_account import Account
from dotenv import load_dotenv

load_dotenv()

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT_DIR = Path(__file__).resolve().parent.parent
ABI_DIR = ROOT_DIR / "contracts" / "abi"
OUTPUT_FILE = ROOT_DIR / "deployed_v2_infrastructure.json"

NETWORK_CONFIGS: Dict[str, Dict[str, Any]] = {
    "base": {
        "name": "Base Mainnet",
        "chain_id": 8453,
        "rpcs": [
            "https://mainnet.base.org",
            "https://base.llamarpc.com",
            "https://1rpc.io/base"
        ],
        "explorer": "https://basescan.org",
        "symbol": "ETH",
        "usdc": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        "gate_router": "0xdC6Cb774d51681Fcbba0E67Ca677dEc5705aaB35",
        "safe_guard": "0xb44Bc2Acdd156cE08b549A00a3102e4B01276654",
        "forensic_signer": "0xA185B43fDD19619f99952AAed6eabf1029bF36a1",
        "logistics_oracle_signer": "0xA185B43fDD19619f99952AAed6eabf1029bF36a1",
        "protocol_fee_splitter": "0xA185B43fDD19619f99952AAed6eabf1029bF36a1"
    },
    "polygon": {
        "name": "Polygon Mainnet",
        "chain_id": 137,
        "rpcs": [
            "https://polygon-rpc.com",
            "https://polygon-bor-rpc.publicnode.com",
            "https://1rpc.io/matic"
        ],
        "explorer": "https://polygonscan.com",
        "symbol": "POL",
        "usdc": "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359",
        "gate_router": "0x8ACafCEce0B1BFE140e75614b90FD1307b6f389d",
        "safe_guard": "0x8c2a8B9Ff05a92ad16E0ED58ac83aD6C11cb18Cb",
        "forensic_signer": "0xA185B43fDD19619f99952AAed6eabf1029bF36a1",
        "logistics_oracle_signer": "0xA185B43fDD19619f99952AAed6eabf1029bF36a1",
        "protocol_fee_splitter": "0xA185B43fDD19619f99952AAed6eabf1029bF36a1"
    },
    "arbitrum": {
        "name": "Arbitrum One",
        "chain_id": 42161,
        "rpcs": [
            "https://arb1.arbitrum.io/rpc",
            "https://arbitrum.llamarpc.com",
            "https://1rpc.io/arb"
        ],
        "explorer": "https://arbiscan.io",
        "symbol": "ETH",
        "usdc": "0xaf88d065e77c8cC2239327C5EDb3A432268e5831",
        "gate_router": "0x99FEd65Cf2D5378182c3481B300124BB1a8Ad278",
        "safe_guard": "0x835D01534A5d2E63D52636FAFB1019F889D1E66B",
        "forensic_signer": "0xA185B43fDD19619f99952AAed6eabf1029bF36a1",
        "logistics_oracle_signer": "0xA185B43fDD19619f99952AAed6eabf1029bF36a1",
        "protocol_fee_splitter": "0xA185B43fDD19619f99952AAed6eabf1029bF36a1"
    }
}


def load_contract_artifact(contract_name: str) -> Tuple[list, str]:
    """Loads ABI and bytecode for given contract from contracts/abi/."""
    artifact_path = ABI_DIR / f"{contract_name}.json"
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Artifact {contract_name}.json not found at {artifact_path}. "
            "Please run `python scripts/compile_contracts.py` first."
        )

    with open(artifact_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    abi = data.get("abi", [])
    bytecode = data.get("bytecode", "")
    if not bytecode.startswith("0x"):
        bytecode = "0x" + bytecode

    if not abi or len(bytecode) <= 2:
        raise ValueError(f"Artifact {contract_name} has empty ABI or bytecode")

    return abi, bytecode


def connect_web3(chain_key: str) -> Tuple[Web3, str]:
    """Connects to Web3 provider with fallback RPC support."""
    config = NETWORK_CONFIGS[chain_key]
    for rpc in config["rpcs"]:
        try:
            w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={"timeout": 12}))
            if w3.is_connected():
                return w3, rpc
        except Exception:
            continue
    raise ConnectionError(f"Failed to connect to any RPC for {config['name']}")


def build_deployment_plan(chain_key: str) -> Dict[str, Any]:
    """Prepares and validates constructor parameters for all V2 contracts."""
    config = NETWORK_CONFIGS[chain_key]
    shield_abi, shield_bin = load_contract_artifact("AgenticShieldPool")
    logistics_abi, logistics_bin = load_contract_artifact("LogisticsPoDEscrow")

    shield_args = [
        Web3.to_checksum_address(config["usdc"]),
        Web3.to_checksum_address(config["gate_router"]),
        Web3.to_checksum_address(config["safe_guard"]),
        Web3.to_checksum_address(config["forensic_signer"])
    ]

    logistics_args = [
        Web3.to_checksum_address(config["usdc"]),
        Web3.to_checksum_address(config["logistics_oracle_signer"]),
        Web3.to_checksum_address(config["protocol_fee_splitter"])
    ]

    return {
        "network": config["name"],
        "chain_id": config["chain_id"],
        "contracts": {
            "AgenticShieldPool": {
                "abi": shield_abi,
                "bytecode": shield_bin,
                "constructor_args": shield_args
            },
            "LogisticsPoDEscrow": {
                "abi": logistics_abi,
                "bytecode": logistics_bin,
                "constructor_args": logistics_args
            }
        }
    }


def deploy_contract(
    w3: Web3,
    account: Any,
    private_key: str,
    chain_id: int,
    abi: list,
    bytecode: str,
    args: list,
    name: str
) -> Dict[str, Any]:
    """Builds, signs, and executes contract deployment transaction."""
    contract = w3.eth.contract(abi=abi, bytecode=bytecode)
    current_nonce = w3.eth.get_transaction_count(account.address, "pending")

    tx_params = {
        "from": account.address,
        "nonce": current_nonce,
        "chainId": chain_id
    }

    try:
        fee_history = w3.eth.fee_history(1, "latest", [50])
        base_fee = fee_history["baseFeePerGas"][-1]
        priority_fee = w3.to_wei(0.001, "gwei")
        tx_params["maxFeePerGas"] = int(base_fee * 1.5) + priority_fee
        tx_params["maxPriorityFeePerGas"] = priority_fee
    except Exception:
        tx_params["gasPrice"] = int(w3.eth.gas_price * 1.2)

    tx = contract.constructor(*args).build_transaction(tx_params)
    estimated_gas = w3.eth.estimate_gas(tx)
    tx["gas"] = int(estimated_gas * 1.3)

    signed_tx = w3.eth.account.sign_transaction(tx, private_key=private_key)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    print(f"  📡 [{name}] Broadcasted Tx: {tx_hash.hex()}")

    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
    print(f"  🎉 [{name}] Deployed at: {receipt.contractAddress} (Block #{receipt.blockNumber}, Gas: {receipt.gasUsed:,})")
    time.sleep(2)

    return {
        "address": receipt.contractAddress,
        "tx_hash": tx_hash.hex(),
        "block_number": receipt.blockNumber,
        "gas_used": receipt.gasUsed
    }


def run_deployment(chain_key: str, dry_run: bool = False) -> Dict[str, Any]:
    """Executes full deployment process for a given network."""
    config = NETWORK_CONFIGS[chain_key]
    print(f"\n========================================================")
    print(f"🚀 Deploying V2 Infrastructure on {config['name']} (Chain ID {config['chain_id']})")
    print(f"========================================================")

    plan = build_deployment_plan(chain_key)

    if dry_run:
        print("🔍 [DRY-RUN / SIMULATION MODE] Verifying parameters and ABI encoding...")
        w3_dummy = Web3()
        for name, cdata in plan["contracts"].items():
            contract = w3_dummy.eth.contract(abi=cdata["abi"], bytecode=cdata["bytecode"])
            encoded_tx = contract.constructor(*cdata["constructor_args"]).build_transaction({
                "from": "0xA185B43fDD19619f99952AAed6eabf1029bF36a1",
                "nonce": 0,
                "gas": 3000000,
                "gasPrice": 1000000000,
                "chainId": config["chain_id"]
            })
            print(f"  ✅ [{name}] Constructor parameters & bytecode validated (data size: {len(encoded_tx['data'])} bytes)")

        return {
            "status": "SIMULATED_SUCCESS",
            "chain_key": chain_key,
            "chain_id": config["chain_id"],
            "contracts": {
                name: {"args": cdata["constructor_args"], "verified": True}
                for name, cdata in plan["contracts"].items()
            }
        }

    # Live Execution
    private_key = os.environ.get("DEPLOYER_PRIVATE_KEY") or os.environ.get("PRIVATE_KEY")
    if not private_key:
        raise ValueError("DEPLOYER_PRIVATE_KEY or PRIVATE_KEY env variable required for live deployment")

    account = Account.from_key(private_key)
    w3, rpc_used = connect_web3(chain_key)
    balance_wei = w3.eth.get_balance(account.address)
    balance_eth = float(w3.from_wei(balance_wei, "ether"))
    print(f"  🔑 Deployer Address: {account.address}")
    print(f"  💰 Native Balance: {balance_eth:.5f} {config['symbol']} (via {rpc_used})")

    if balance_eth < 0.0005:
        print(f"  ⚠️ Warning: Low balance for deployment ({balance_eth} {config['symbol']}). Proceeding with gas estimation...")

    deployed_records = {}
    for name, cdata in plan["contracts"].items():
        rec = deploy_contract(
            w3=w3,
            account=account,
            private_key=private_key,
            chain_id=config["chain_id"],
            abi=cdata["abi"],
            bytecode=cdata["bytecode"],
            args=cdata["constructor_args"],
            name=name
        )
        deployed_records[name] = {
            "address": rec["address"],
            "tx_hash": rec["tx_hash"],
            "block_number": rec["block_number"],
            "gas_used": rec["gas_used"],
            "explorer_url": f"{config['explorer']}/address/{rec['address']}"
        }

    result = {
        "network": config["name"],
        "chain_id": config["chain_id"],
        "deployer": account.address,
        "deployed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "contracts": deployed_records
    }

    # Save to json file
    existing_data = {}
    if OUTPUT_FILE.exists():
        try:
            with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
        except Exception:
            existing_data = {}

    existing_data[chain_key] = result
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(existing_data, f, indent=2)

    print(f"💾 Saved deployment record to {OUTPUT_FILE}")
    return result


def main():
    parser = argparse.ArgumentParser(description="Deploy V2 Infrastructure (AgenticShieldPool & LogisticsPoDEscrow)")
    parser.add_argument("--chain", choices=["base", "polygon", "arbitrum"], default="base", help="Target blockchain")
    parser.add_argument("--all", action="store_true", help="Deploy to all supported chains")
    parser.add_argument("--dry-run", action="store_true", help="Simulate encoding and validation without broadcasting tx")
    args = parser.parse_args()

    chains = list(NETWORK_CONFIGS.keys()) if args.all else [args.chain]
    for chain in chains:
        run_deployment(chain, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
