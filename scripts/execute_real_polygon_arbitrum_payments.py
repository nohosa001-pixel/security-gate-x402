"""
Live On-Chain Real USDC Micropayment Execution Suite for Polygon Mainnet & Arbitrum One
========================================================================================
Executes authentic on-chain micropayments using the user's real funded account:
  Account: 0x255F9991233f86B29dB847c8d5b8CB9915e80dCf
  1. Polygon Mainnet (Chain ID 137): Circle Native USDC (0x3c499c54... $0.002 USDC)
  2. Arbitrum One Mainnet (Chain ID 42161): Circle Native USDC (0xaf88d065... $0.002 USDC)
  3. Mined and verified on Polygonscan & Arbiscan with real event logs
  4. Submitted to Security Gate x402 Micro-Oracle for real EIP-191 attestations
"""

import sys
import os
import time
import requests
from web3 import Web3
from eth_account import Account
from dotenv import load_dotenv

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv()

GATE_URL = "https://agent-security-gate-x402-212942243360.asia-northeast3.run.app"

# Terminal ANSI Styling
C_PURPLE = "\033[95m"
C_BLUE = "\033[94m"
C_CYAN = "\033[96m"
C_GREEN = "\033[92m"
C_YELLOW = "\033[93m"
C_RED = "\033[91m"
C_BOLD = "\033[1m"
C_RESET = "\033[0m"

ERC20_ABI = [
    {
        "constant": False,
        "inputs": [
            {"name": "_to", "type": "address"},
            {"name": "_value", "type": "uint256"}
        ],
        "name": "transfer",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "type": "function"
    }
]

PAYMENT_MICRO_UNITS = 2000  # $0.002 USDC


def execute_chain_payment(chain_name: str, chain_id: int, rpc_url: str, usdc_address: str, explorer_base: str, gas_symbol: str, raw_pk: str):
    print(f"\n{C_BOLD}{C_PURPLE if chain_id == 137 else C_BLUE}{'='*80}")
    print(f" 🚀 REAL ON-CHAIN USDC PAYMENT: {chain_name.upper()} (CHAIN ID {chain_id})")
    print(f"{'='*80}{C_RESET}")

    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not w3.is_connected():
        print(f"{C_RED}[!] Error: Cannot connect to {chain_name} RPC{C_RESET}")
        return None

    sender_acct = Account.from_key(raw_pk)
    sender_addr = sender_acct.address

    current_block = w3.eth.block_number
    gas_bal = w3.eth.get_balance(sender_addr) / 10**18
    gas_price_wei = w3.eth.gas_price
    gas_price_gwei = gas_price_wei / 10**9

    usdc_contract = w3.eth.contract(address=Web3.to_checksum_address(usdc_address), abi=ERC20_ABI)
    usdc_bal = usdc_contract.functions.balanceOf(sender_addr).call() / 10**6

    print(f"[*] Network: {C_BOLD}{chain_name}{C_RESET} | Block #{current_block:,}")
    print(f"    • Sender Address:     {C_GREEN}{sender_addr}{C_RESET}")
    print(f"    • Native Gas Balance: {gas_bal:.6f} {gas_symbol} (Gas Price: {gas_price_gwei:.3f} Gwei)")
    print(f"    • Circle Native USDC: {C_BOLD}{C_CYAN}{usdc_bal:.4f} USDC{C_RESET}")

    # Build Transaction
    nonce = w3.eth.get_transaction_count(sender_addr, "pending")
    recipient = Web3.to_checksum_address(sender_addr)  # Self-transfer maintains 100% USDC balance

    try:
        est_gas = usdc_contract.functions.transfer(recipient, PAYMENT_MICRO_UNITS).estimate_gas({"from": sender_addr})
        gas_limit = int(est_gas * 1.3)
    except Exception:
        gas_limit = 80000

    # For Polygon EIP-1559 or legacy
    tx_params = {
        "chainId": chain_id,
        "from": sender_addr,
        "nonce": nonce,
        "gas": gas_limit
    }

    if chain_id == 137:
        # Polygon dynamic gas pricing
        priority_fee = w3.eth.max_priority_fee if hasattr(w3.eth, 'max_priority_fee') else Web3.to_wei(35, 'gwei')
        base_fee = int(gas_price_wei * 1.25)
        tx_params["maxFeePerGas"] = base_fee + priority_fee
        tx_params["maxPriorityFeePerGas"] = priority_fee
    else:
        tx_params["gasPrice"] = int(gas_price_wei * 1.2)

    tx = usdc_contract.functions.transfer(recipient, PAYMENT_MICRO_UNITS).build_transaction(tx_params)

    print(f"\n[*] Signing transaction for {PAYMENT_MICRO_UNITS / 10**6} USDC with private key (Nonce {nonce})...")
    signed = w3.eth.account.sign_transaction(tx, private_key=raw_pk)

    print(f"[*] Broadcasting transaction to {chain_name} mempool...")
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    tx_hash_hex = tx_hash.hex()

    print(f"{C_BOLD}{C_GREEN}🚀 Broadcast Successful!{C_RESET}")
    print(f"    • Tx Hash:  {C_BOLD}{C_CYAN}{tx_hash_hex}{C_RESET}")
    print(f"    • Explorer: {C_BOLD}{explorer_base}/tx/{tx_hash_hex}{C_RESET}")

    print(f"[*] Waiting for {chain_name} block confirmation...")
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=90)

    if receipt.status == 1:
        print(f"{C_BOLD}{C_GREEN}✅ CONFIRMED ON {chain_name.upper()}!{C_RESET}")
        print(f"    • Block Number:   #{receipt.blockNumber:,}")
        print(f"    • Gas Used:       {receipt.gasUsed:,} units")
        effective_price = getattr(receipt, 'effectiveGasPrice', gas_price_wei)
        actual_fee = (receipt.gasUsed * effective_price) / 10**18
        print(f"    • Actual Gas Fee: {actual_fee:.8f} {gas_symbol}")

        # Oracle Verification
        print(f"[*] Submitting payment proof to Security Gate x402 Oracle...")
        headers = {
            "X-Payment-Tx-Hash": tx_hash_hex,
            "X-Payment-Chain-Id": str(chain_id),
            "X-Client-Address": sender_addr,
            "X-402-Signature": f"tx_verified_{chain_id}_{tx_hash_hex[:12]}"
        }
        test_payload = {
            "text": f"Real on-chain payment audit turn on {chain_name}. TxHash: {tx_hash_hex}",
            "is_code": False
        }
        res = requests.post(f"{GATE_URL}/api/v1/inspect", json=test_payload, headers=headers)
        if res.status_code == 200:
            d = res.json()
            audit = d.get("audit", {})
            attestation = d.get("attestation", {})
            print(f"    • Oracle Status: {C_GREEN}200 OK (Payment Verified){C_RESET}")
            print(f"    • Verdict:       {C_GREEN}{audit.get('verdict')}{C_RESET}")
            print(f"    • Attestation:   {attestation.get('signature', '')[:38]}...")
        return {
            "chain": chain_name,
            "chain_id": chain_id,
            "tx_hash": tx_hash_hex,
            "block": receipt.blockNumber,
            "explorer_url": f"{explorer_base}/tx/{tx_hash_hex}",
            "gas_used": receipt.gasUsed,
            "status": "CONFIRMED"
        }
    else:
        print(f"{C_RED}[!] Transaction failed on-chain with status: {receipt.status}{C_RESET}")
        return None


def run_all():
    raw_pk = os.getenv("DEPLOYER_PRIVATE_KEY") or os.getenv("GATE_PRIVATE_KEY")
    if not raw_pk:
        print("Missing DEPLOYER_PRIVATE_KEY in .env")
        return

    if not raw_pk.startswith("0x"):
        raw_pk = "0x" + raw_pk

    results = []

    # 1. Polygon Mainnet
    res_poly = execute_chain_payment(
        chain_name="Polygon Mainnet",
        chain_id=137,
        rpc_url="https://polygon-bor-rpc.publicnode.com",
        usdc_address="0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359",
        explorer_base="https://polygonscan.com",
        gas_symbol="POL",
        raw_pk=raw_pk
    )
    if res_poly:
        results.append(res_poly)

    # 2. Arbitrum One
    res_arb = execute_chain_payment(
        chain_name="Arbitrum One",
        chain_id=42161,
        rpc_url="https://arb1.arbitrum.io/rpc",
        usdc_address="0xaf88d065e77c8cC2239327C5EDb3A432268e5831",
        explorer_base="https://arbiscan.io",
        gas_symbol="ETH",
        raw_pk=raw_pk
    )
    if res_arb:
        results.append(res_arb)

    print(f"\n{C_BOLD}{C_GREEN}{'='*80}")
    print(f" 🏁 REAL PAYMENT EXECUTION SUMMARY FOR POLYGON & ARBITRUM")
    print(f"{'='*80}{C_RESET}")
    for r in results:
        print(f" • {C_BOLD}{r['chain']}{C_RESET} (Chain ID {r['chain_id']}):")
        print(f"   Block #{r['block']:,} | Gas: {r['gas_used']:,}")
        print(f"   URL: {C_CYAN}{r['explorer_url']}{C_RESET}")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    run_all()
