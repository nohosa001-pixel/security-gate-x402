#!/usr/bin/env python3
"""
A.GRID Quad-Chain Autonomous On-Chain Volume Daemon
===================================================
Continuously rotates and broadcasts real-time micro-toll settlements across:
1. Base Mainnet (Chain ID 8453)
2. Arbitrum One Mainnet (Chain ID 42161)
3. Polygon Mainnet (Chain ID 137)
4. Solana Mainnet (501) - Active when funded

Destination: Sovereign Protocol Treasury (0xA185B43fDD19619f99952AAed6eabf1029bF36a1 / 411ks...)
Payload Tag: x402_protocol_toll
"""

import os
import sys
import time
import json
import struct
import base64
import argparse
import urllib.request
from web3 import Web3
from cryptography.hazmat.primitives.asymmetric import ed25519

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WALLET_EVM_FILE = os.path.join(ROOT_DIR, "data", "bot_wallet_evm.json")
WALLET_SOL_FILE = os.path.join(ROOT_DIR, "data", "bot_wallet_solana.json")

TREASURY_EVM = "0xA185B43fDD19619f99952AAed6eabf1029bF36a1"
TREASURY_SOL = "411ksMz9RHYVtVMe6RUUErzZYtrU9zzvkgzswKbqx9qp"
TAG_CALLDATA = "0x783430325f70726f746f636f6c5f746f6c6c"  # "x402_protocol_toll"

ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"

def b58decode(v: str) -> bytes:
    n = 0
    for char in v:
        n = n * 58 + ALPHABET.index(char)
    res = n.to_bytes((n.bit_length() + 7) // 8, "big") if n > 0 else b""
    pad = len(v) - len(v.lstrip("1"))
    return b"\x00" * pad + res

SYSTEM_PROGRAM_ID = b58decode("11111111111111111111111111111111")

EVM_NETWORKS = {
    "base": {
        "name": "Base Mainnet",
        "chain_id": 8453,
        "rpcs": [os.getenv("BASE_RPC_URL", "https://mainnet.base.org"), "https://base.llamarpc.com", "https://1rpc.io/base"],
        "explorer": "https://basescan.org/tx/0x"
    },
    "arbitrum": {
        "name": "Arbitrum One",
        "chain_id": 42161,
        "rpcs": [os.getenv("ARBITRUM_RPC_URL", "https://arb1.arbitrum.io/rpc"), "https://arbitrum.llamarpc.com", "https://1rpc.io/arb"],
        "explorer": "https://arbiscan.io/tx/0x"
    },
    "polygon": {
        "name": "Polygon Mainnet",
        "chain_id": 137,
        "rpcs": ["https://1rpc.io/matic", "https://polygon-rpc.com", "https://rpc.ankr.com/polygon", "https://polygon.llamarpc.com"],
        "explorer": "https://polygonscan.com/tx/0x"
    }
}


def load_evm_wallet():
    with open(WALLET_EVM_FILE, "r") as f:
        return json.load(f)


def load_sol_wallet():
    if os.path.exists(WALLET_SOL_FILE):
        with open(WALLET_SOL_FILE, "r") as f:
            return json.load(f)
    return None


def send_evm_micro_toll(network_key: str, wallet: dict) -> dict:
    cfg = EVM_NETWORKS[network_key]
    last_err = "No RPC endpoints configured"
    addr = wallet["address"]
    pk = wallet["private_key"]

    for endpoint in cfg["rpcs"]:
        try:
            w3 = Web3(Web3.HTTPProvider(endpoint, request_kwargs={"timeout": 10}))
            if not w3.is_connected():
                continue

            nonce = w3.eth.get_transaction_count(addr)
            gas_price = w3.eth.gas_price

            tx = {
                "to": TREASURY_EVM,
                "value": w3.to_wei(0.000001, "ether") if network_key != "polygon" else w3.to_wei(0.001, "ether"),
                "gas": 45000,
                "gasPrice": int(gas_price * 1.3),
                "nonce": nonce,
                "chainId": cfg["chain_id"],
                "data": TAG_CALLDATA
            }

            signed_tx = w3.eth.account.sign_transaction(tx, private_key=pk)
            tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            tx_hex = tx_hash.hex()

            receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=45)
            return {
                "success": receipt.status == 1,
                "network": cfg["name"],
                "tx_hash": f"0x{tx_hex}",
                "block": receipt.blockNumber,
                "explorer_url": f"{cfg['explorer']}{tx_hex}"
            }
        except Exception as exc:
            last_err = str(exc)
            continue

    return {"success": False, "network": cfg["name"], "error": last_err}


def send_solana_micro_toll(sol_wallet: dict, lamports: int = 5000) -> dict:
    rpc_url = os.getenv("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com")
    try:
        full_keypair_bytes = b58decode(sol_wallet["private_key_b58"])
        priv_bytes = full_keypair_bytes[:32]
        pub_bytes = full_keypair_bytes[32:]

        # 1. Check balance
        bal_body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "getBalance", "params": [sol_wallet["address"]]}).encode("utf-8")
        req_bal = urllib.request.Request(rpc_url, data=bal_body, headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req_bal, timeout=10) as r:
            res_bal = json.loads(r.read().decode("utf-8"))
            bal = res_bal.get("result", {}).get("value", 0)
            if bal < lamports + 5000:
                return {"success": False, "network": "Solana Mainnet", "error": f"Insufficient SOL balance ({bal / 1e9} SOL). Awaiting deposit."}

        # 2. Latest Blockhash
        bh_body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "getLatestBlockhash", "params": [{"commitment": "finalized"}]}).encode("utf-8")
        req_bh = urllib.request.Request(rpc_url, data=bh_body, headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req_bh, timeout=10) as r:
            res_bh = json.loads(r.read().decode("utf-8"))
            blockhash_b58 = res_bh["result"]["value"]["blockhash"]
            blockhash_bytes = b58decode(blockhash_b58)

        # 3. Build & Sign Transaction
        recipient_bytes = b58decode(TREASURY_SOL)
        accounts = [pub_bytes, recipient_bytes, SYSTEM_PROGRAM_ID]
        account_keys = b"".join(accounts)
        instruction_data = struct.pack("<IQ", 2, lamports)
        compiled_instruction = bytes([2, 2, 0, 1, len(instruction_data)]) + instruction_data
        header = bytes([1, 0, 1])
        message = header + bytes([3]) + account_keys + blockhash_bytes + bytes([1]) + compiled_instruction

        priv_key = ed25519.Ed25519PrivateKey.from_private_bytes(priv_bytes)
        signature = priv_key.sign(message)
        tx_bytes = bytes([1]) + signature + message
        tx_b64 = base64.b64encode(tx_bytes).decode("utf-8")

        # 4. Broadcast
        send_body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "sendTransaction", "params": [tx_b64, {"encoding": "base64"}]}).encode("utf-8")
        req_send = urllib.request.Request(rpc_url, data=send_body, headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req_send, timeout=10) as r:
            res_send = json.loads(r.read().decode("utf-8"))
            if "error" in res_send:
                return {"success": False, "network": "Solana Mainnet", "error": str(res_send["error"])}
            tx_sig = res_send["result"]
            return {
                "success": True,
                "network": "Solana Mainnet",
                "tx_hash": tx_sig,
                "block": "Confirmed",
                "explorer_url": f"https://solscan.io/tx/{tx_sig}"
            }
    except Exception as exc:
        return {"success": False, "network": "Solana Mainnet", "error": str(exc)}


def main():
    parser = argparse.ArgumentParser(description="A.GRID Quad-Chain Autonomous Volume Daemon")
    parser.add_argument("--interval", type=int, default=180, help="Interval in seconds between cycles (default: 180s)")
    parser.add_argument("--iterations", type=int, default=0, help="Number of cycles to execute (default: 0 = infinite)")
    args = parser.parse_args()

    evm_wallet = load_evm_wallet()
    sol_wallet = load_sol_wallet()

    print("=" * 80)
    print("🤖 [A.GRID QUAD-CHAIN ON-CHAIN VOLUME DAEMON]")
    print(f"• EVM Bot Address   : {evm_wallet['address']}")
    if sol_wallet:
        print(f"• Solana Bot Address: {sol_wallet['address']}")
    print(f"• Sovereign Treasury: EVM: {TREASURY_EVM} | SOL: {TREASURY_SOL}")
    print(f"• Active Networks   : Base, Arbitrum One, Polygon, & Solana")
    print(f"• Interval          : {args.interval}s")
    print("=" * 80)
    sys.stdout.flush()

    cycle_plan = ["base", "arbitrum", "polygon", "solana"]
    count = 0
    try:
        while True:
            target = cycle_plan[count % len(cycle_plan)]
            t_now = time.strftime("%Y-%m-%d %H:%M:%S")

            if target in EVM_NETWORKS:
                print(f"\n[{t_now}] [Cycle #{count + 1}] Broadcasting micro-settlement to {EVM_NETWORKS[target]['name']}...")
                res = send_evm_micro_toll(target, evm_wallet)
            else:
                print(f"\n[{t_now}] [Cycle #{count + 1}] Broadcasting micro-settlement to Solana Mainnet...")
                if sol_wallet:
                    res = send_solana_micro_toll(sol_wallet)
                else:
                    res = {"success": False, "error": "Solana wallet not initialized"}

            if res.get("success"):
                print(f"  ✅ SUCCESS on {res['network']} (Block/State: {res.get('block', 'Confirmed')})")
                print(f"  🔗 Explorer: {res.get('explorer_url', '')}")
            else:
                print(f"  ℹ️ {res.get('network', target)} Notice: {res.get('error')}")

            count += 1
            if args.iterations > 0 and count >= args.iterations:
                print(f"\n✨ Completed requested {args.iterations} volume cycles.")
                sys.stdout.flush()
                break

            print(f"  ⏳ Sleeping {args.interval}s until next on-chain cycle...")
            sys.stdout.flush()
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\n🛑 Daemon stopped by user.")


if __name__ == "__main__":
    main()
