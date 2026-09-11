"""
Batch Deployment Script for Core On-Chain Agent Infrastructure across Base & Arbitrum.
Deploys:
1. SafeSecurityGateGuard.sol (Safe Treasury Capital Defense Guard)
2. AgentCreditOracle.sol (Agent Credit Rating & Uncollateralized Loan Oracle)
3. AgentTreasuryVault.sol (AI Agent Asset Management & Trading Vault)
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

NETWORKS = {
    "base": {
        "name": "Base Mainnet",
        "chain_id": 8453,
        "rpc": "https://mainnet.base.org",
        "usdc": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        "explorer": "https://basescan.org"
    },
    "arbitrum": {
        "name": "Arbitrum One",
        "chain_id": 42161,
        "rpc": "https://arb1.arbitrum.io/rpc",
        "usdc": "0xaf88d065e77c8cC2239327C5EDb3A432268e5831",
        "explorer": "https://arbiscan.io"
    }
}


def compile_all():
    print("\n📦 Compiling Solidity contracts (v0.8.20 with via-IR optimizer)...")
    solcx.install_solc("0.8.20")
    files = [
        "contracts/SafeSecurityGateGuard.sol",
        "contracts/AgentCreditOracle.sol",
        "contracts/AgentTreasuryVault.sol"
    ]
    compiled = solcx.compile_files(
        files,
        solc_version="0.8.20",
        via_ir=True,
        optimize=True,
        optimize_runs=200,
        output_values=["abi", "bin"]
    )
    print("✅ All contracts compiled successfully!")
    return compiled


def get_contract_data(compiled, name):
    for k, v in compiled.items():
        if k.endswith(f":{name}"):
            return v
    raise KeyError(f"Contract {name} not found in compiled outputs")


def deploy_single(w3, account, private_key, chain_id, abi, bytecode, constructor_args, name):
    contract = w3.eth.contract(abi=abi, bytecode=bytecode)
    current_nonce = w3.eth.get_transaction_count(account.address)

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
        tx_params["gasPrice"] = w3.eth.gas_price

    tx = contract.constructor(*constructor_args).build_transaction(tx_params)
    estimated_gas = w3.eth.estimate_gas(tx)
    tx["gas"] = int(estimated_gas * 1.25)

    signed_tx = w3.eth.account.sign_transaction(tx, private_key=private_key)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    print(f"  📡 [{name}] Broadcasted Tx: {tx_hash.hex()}")

    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
    print(f"  🎉 [{name}] Deployed at: {receipt.contractAddress} (Block #{receipt.blockNumber}, Gas: {receipt.gasUsed:,})")
    time.sleep(2)
    return receipt.contractAddress, tx_hash.hex()


def main():
    deployer_pk = os.getenv("DEPLOYER_PRIVATE_KEY") or os.getenv("GATE_PRIVATE_KEY")
    if not deployer_pk:
        print("[ERROR] Missing DEPLOYER_PRIVATE_KEY in .env")
        sys.exit(1)

    deployer_pk = deployer_pk.strip().strip('"').strip("'")
    if not deployer_pk.startswith("0x"):
        deployer_pk = "0x" + deployer_pk

    account = Account.from_key(deployer_pk)
    oracle_signer = os.getenv("SERVER_WALLET_ADDRESS", account.address)

    print("=" * 80)
    print(f"🚀 [MULTI-CHAIN CORE INFRASTRUCTURE DEPLOYMENT]")
    print(f"👛 Deployer Address: {account.address}")
    print(f"🛡️ Oracle Signer:   {oracle_signer}")
    print("=" * 80)

    compiled = compile_all()
    guard_data = get_contract_data(compiled, "SafeSecurityGateGuard")
    credit_data = get_contract_data(compiled, "AgentCreditOracle")
    vault_data = get_contract_data(compiled, "AgentTreasuryVault")

    results = {}

    for net_key, conf in NETWORKS.items():
        print(f"\n{'='*40}\n🌐 Deploying to {conf['name']} (Chain ID: {conf['chain_id']})\n{'='*40}")
        w3 = Web3(Web3.HTTPProvider(conf["rpc"], request_kwargs={"timeout": 15}))
        bal = w3.eth.get_balance(account.address) / 1e18
        print(f"💰 Balance on {conf['name']}: {bal:.6f} ETH")

        results[net_key] = {}

        # 1. SafeSecurityGateGuard
        print("\n1️⃣ Deploying SafeSecurityGateGuard.sol...")
        guard_addr, guard_tx = deploy_single(
            w3, account, deployer_pk, conf["chain_id"],
            guard_data["abi"], guard_data["bin"],
            [oracle_signer, 30],
            "SafeSecurityGateGuard"
        )
        results[net_key]["safe_guard_address"] = guard_addr
        results[net_key]["safe_guard_tx"] = guard_tx

        # 2. AgentCreditOracle
        print("\n2️⃣ Deploying AgentCreditOracle.sol...")
        credit_addr, credit_tx = deploy_single(
            w3, account, deployer_pk, conf["chain_id"],
            credit_data["abi"], credit_data["bin"],
            [oracle_signer],
            "AgentCreditOracle"
        )
        results[net_key]["credit_oracle_address"] = credit_addr
        results[net_key]["credit_oracle_tx"] = credit_tx

        # 3. AgentTreasuryVault
        print("\n3️⃣ Deploying AgentTreasuryVault.sol...")
        vault_addr, vault_tx = deploy_single(
            w3, account, deployer_pk, conf["chain_id"],
            vault_data["abi"], vault_data["bin"],
            [conf["usdc"], oracle_signer, oracle_signer],
            "AgentTreasuryVault"
        )
        results[net_key]["vault_contract_address"] = vault_addr
        results[net_key]["vault_contract_tx"] = vault_tx

    out_file = Path("deployed_infrastructure_multichain.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print("\n" + "=" * 80)
    print(f"✨ [SUCCESS] All 6 Core Infrastructure Contracts Deployed & Saved to {out_file.name}!")
    print("=" * 80)


if __name__ == "__main__":
    main()
