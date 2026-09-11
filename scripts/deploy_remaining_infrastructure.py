"""
Batch Deployment Script for the Remaining 5 Agent Infrastructure Contracts across Base & Arbitrum.
Deploys:
1. AgentComplianceRegistry.sol (EU AI Act & Compliance Registry)
2. AgentEscrow.sol (Task Performance Escrow & Slashing)
3. AgentInsurancePool.sol (AI Malpractice & Prompt Injection Liability Insurance)
4. AgentLendingPool.sol (Uncollateralized Credit Line Lending Pool)
5. AgentFactoringPool.sol (Invoice & A2A Receivables Factoring Pool)
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
        "credit_oracle": "0x227e1129Ba9B39a50fb9E0802bA13A7F77Debe93"
    },
    "arbitrum": {
        "name": "Arbitrum One",
        "chain_id": 42161,
        "rpc": "https://arb1.arbitrum.io/rpc",
        "usdc": "0xaf88d065e77c8cC2239327C5EDb3A432268e5831",
        "credit_oracle": "0x227e1129Ba9B39a50fb9E0802bA13A7F77Debe93"
    }
}


def compile_remaining():
    print("\n📦 Compiling remaining 5 Solidity contracts (v0.8.20 with via-IR optimizer)...")
    solcx.install_solc("0.8.20")
    files = [
        "contracts/AgentComplianceRegistry.sol",
        "contracts/AgentEscrow.sol",
        "contracts/AgentInsurancePool.sol",
        "contracts/AgentLendingPool.sol",
        "contracts/AgentFactoringPool.sol"
    ]
    compiled = solcx.compile_files(
        files,
        solc_version="0.8.20",
        via_ir=True,
        optimize=True,
        optimize_runs=200,
        output_values=["abi", "bin"]
    )
    print("✅ All remaining contracts compiled successfully!")
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
    print(f"  📡 [{name}] Tx Broadcasted: {tx_hash.hex()}")

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
    print(f"🚀 [MULTI-CHAIN REMAINING 5 CONTRACTS DEPLOYMENT]")
    print(f"👛 Deployer Address: {account.address}")
    print(f"🛡️ Oracle Signer:   {oracle_signer}")
    print("=" * 80)

    compiled = compile_remaining()
    compliance_data = get_contract_data(compiled, "AgentComplianceRegistry")
    escrow_data = get_contract_data(compiled, "AgentEscrow")
    insurance_data = get_contract_data(compiled, "AgentInsurancePool")
    lending_data = get_contract_data(compiled, "AgentLendingPool")
    factoring_data = get_contract_data(compiled, "AgentFactoringPool")

    results = {}

    for net_key, conf in NETWORKS.items():
        print(f"\n{'='*40}\n🌐 Deploying 5 contracts to {conf['name']} (Chain ID: {conf['chain_id']})\n{'='*40}")
        w3 = Web3(Web3.HTTPProvider(conf["rpc"], request_kwargs={"timeout": 15}))
        bal = w3.eth.get_balance(account.address) / 1e18
        print(f"💰 Balance on {conf['name']}: {bal:.6f} ETH")

        results[net_key] = {}

        # 1. AgentComplianceRegistry
        print("\n1️⃣ Deploying AgentComplianceRegistry.sol...")
        comp_addr, comp_tx = deploy_single(
            w3, account, deployer_pk, conf["chain_id"],
            compliance_data["abi"], compliance_data["bin"],
            [oracle_signer],
            "AgentComplianceRegistry"
        )
        results[net_key]["compliance_registry"] = comp_addr

        # 2. AgentEscrow
        print("\n2️⃣ Deploying AgentEscrow.sol...")
        escrow_addr, escrow_tx = deploy_single(
            w3, account, deployer_pk, conf["chain_id"],
            escrow_data["abi"], escrow_data["bin"],
            [conf["usdc"], oracle_signer],
            "AgentEscrow"
        )
        results[net_key]["agent_escrow"] = escrow_addr

        # 3. AgentInsurancePool
        print("\n3️⃣ Deploying AgentInsurancePool.sol...")
        ins_addr, ins_tx = deploy_single(
            w3, account, deployer_pk, conf["chain_id"],
            insurance_data["abi"], insurance_data["bin"],
            [conf["usdc"], oracle_signer, oracle_signer],
            "AgentInsurancePool"
        )
        results[net_key]["insurance_pool"] = ins_addr

        # 4. AgentLendingPool
        print("\n4️⃣ Deploying AgentLendingPool.sol...")
        lend_addr, lend_tx = deploy_single(
            w3, account, deployer_pk, conf["chain_id"],
            lending_data["abi"], lending_data["bin"],
            [conf["usdc"], conf["credit_oracle"]],
            "AgentLendingPool"
        )
        results[net_key]["lending_pool"] = lend_addr

        # 5. AgentFactoringPool
        print("\n5️⃣ Deploying AgentFactoringPool.sol...")
        fact_addr, fact_tx = deploy_single(
            w3, account, deployer_pk, conf["chain_id"],
            factoring_data["abi"], factoring_data["bin"],
            [conf["usdc"], oracle_signer, oracle_signer],
            "AgentFactoringPool"
        )
        results[net_key]["factoring_pool"] = fact_addr

    out_file = Path("deployed_full_suite_multichain.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print("\n" + "=" * 80)
    print(f"✨ [FULL SUITE SUCCESS] 100% All Contracts Deployed across Base & Arbitrum! Saved to {out_file.name}")
    print("=" * 80)


if __name__ == "__main__":
    main()
