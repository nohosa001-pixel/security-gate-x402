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
    "https://polygon-bor-rpc.publicnode.com",
    "https://polygon.llamarpc.com",
    "https://1rpc.io/matic"
]

POLYGON_USDC_NATIVE = "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359"
ORACLE_SIGNER = "0x255F9991233f86B29dB847c8d5b8CB9915e80dCf"
ORACLE_TREASURY = "0x255F9991233f86B29dB847c8d5b8CB9915e80dCf"


def get_web3():
    for rpc in RPC_ENDPOINTS:
        try:
            w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={"timeout": 15, "headers": {"User-Agent": "Mozilla/5.0"}}))
            if w3.is_connected():
                return w3, rpc
        except Exception:
            continue
    raise ConnectionError("Failed to connect to any Polygon Mainnet RPC endpoint.")


def main():
    print("=" * 80)
    print("🚀 [REDEPLOYING AgentInsurancePool.sol TO POLYGON MAINNET]")
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
    print(f"👛 Deployer Address: {account.address}")
    print(f"💰 Deployer Balance: {balance_wei / 1e18:.4f} POL")

    if balance_wei < 0.1 * 1e18:
        print("[ERROR] Insufficient POL balance for deployment.")
        sys.exit(1)

    # 1. Compile with standard json to match verification exactly
    standard_json_path = Path("contracts/verification/AgentInsurancePool.standard.json")
    print(f"📦 Loading Standard JSON: {standard_json_path}")
    with open(standard_json_path, "r", encoding="utf-8") as f:
        input_json = json.load(f)

    solcx.install_solc("0.8.20")
    compiled = solcx.compile_standard(input_json, solc_version="0.8.20")
    contract_data = compiled["contracts"]["contracts/AgentInsurancePool.sol"]["AgentInsurancePool"]
    abi = contract_data["abi"]
    bytecode = contract_data["evm"]["bytecode"]["object"]
    print(f"✅ Compilation complete. Bytecode length: {len(bytecode)} characters")

    contract = w3.eth.contract(abi=abi, bytecode=bytecode)
    constructor_args = [POLYGON_USDC_NATIVE, ORACLE_SIGNER, ORACLE_TREASURY]

    nonce = w3.eth.get_transaction_count(account.address, "pending")
    gas_price = int(w3.eth.gas_price * 1.35)
    print(f"⚡ Current Nonce: {nonce}, Gas Price: {gas_price / 1e9:.2f} Gwei")

    tx_params = {
        "from": account.address,
        "nonce": nonce,
        "gasPrice": gas_price,
        "chainId": 137
    }

    tx = contract.constructor(*constructor_args).build_transaction(tx_params)

    # Estimate gas and apply a safe 30% margin, or cap safely at 3,500,000
    try:
        est_gas = w3.eth.estimate_gas(tx)
        print(f"⛽ Estimated Gas: {est_gas:,}")
        tx["gas"] = int(est_gas * 1.3)
    except Exception as e:
        print(f"⚠️ Gas estimation error ({e}), using safe fallback 3,500,000 gas")
        tx["gas"] = 3500000

    print(f"🚀 Gas limit set to: {tx['gas']:,}")

    signed_tx = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    print(f"📡 Broadcast TX: https://polygonscan.com/tx/{tx_hash.hex()}")
    print("⏳ Waiting for block confirmation...")

    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
    if receipt.status != 1:
        print(f"❌ Deployment failed with status 0! Gas used: {receipt.gasUsed:,}")
        sys.exit(1)

    new_address = receipt.contractAddress
    print(f"🎉 AgentInsurancePool SUCCESSFULLY DEPLOYED AT: {new_address}")
    print(f"⛽ Gas Used: {receipt.gasUsed:,} (Block #{receipt.blockNumber})")

    # Update deployed_contracts_polygon.json
    state_file = "deployed_contracts_polygon.json"
    if os.path.exists(state_file):
        with open(state_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["contracts"]["AgentInsurancePool"] = new_address
        data["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"📝 Updated {state_file} with new address: {new_address}")

    # Return success
    return new_address, tx_hash.hex()


if __name__ == "__main__":
    main()
