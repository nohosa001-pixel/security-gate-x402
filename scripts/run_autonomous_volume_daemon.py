#!/usr/bin/env python3
"""
A.GRID Multi-Chain Autonomous On-Chain Volume Daemon
===================================================
Automatically rotates and broadcasts real-time micro-toll settlements across:
1. Base Mainnet (Chain ID 8453)
2. Arbitrum One Mainnet (Chain ID 42161)

Destination: Sovereign Protocol Treasury (0xA185B43fDD19619f99952AAed6eabf1029bF36a1)
Payload Tag: x402_protocol_toll
"""

import os
import sys
import time
import json
import argparse
from web3 import Web3

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WALLET_FILE = os.path.join(ROOT_DIR, "data", "bot_wallet_evm.json")

TREASURY_ADDRESS = "0xA185B43fDD19619f99952AAed6eabf1029bF36a1"
TAG_CALLDATA = "0x783430325f70726f746f636f6c5f746f6c6c"  # "x402_protocol_toll"

NETWORKS = {
    "base": {
        "name": "Base Mainnet",
        "chain_id": 8453,
        "rpc": os.getenv("BASE_RPC_URL", "https://mainnet.base.org"),
        "explorer": "https://basescan.org/tx/0x"
    },
    "arbitrum": {
        "name": "Arbitrum One",
        "chain_id": 42161,
        "rpc": os.getenv("ARBITRUM_RPC_URL", "https://arb1.arbitrum.io/rpc"),
        "explorer": "https://arbiscan.io/tx/0x"
    }
}


def load_wallet():
    if not os.path.exists(WALLET_FILE):
        raise FileNotFoundError(f"Bot wallet file not found: {WALLET_FILE}")
    with open(WALLET_FILE, "r") as f:
        return json.load(f)


def send_micro_toll(network_key: str, wallet: dict) -> dict:
    cfg = NETWORKS[network_key]
    w3 = Web3(Web3.HTTPProvider(cfg["rpc"]))
    if not w3.is_connected():
        return {"success": False, "error": f"Failed to connect to {cfg['name']} RPC"}

    addr = wallet["address"]
    pk = wallet["private_key"]

    nonce = w3.eth.get_transaction_count(addr)
    gas_price = w3.eth.gas_price

    tx = {
        "to": TREASURY_ADDRESS,
        "value": w3.to_wei(0.000001, "ether"),
        "gas": 40000,
        "gasPrice": int(gas_price * 1.2),
        "nonce": nonce,
        "chainId": cfg["chain_id"],
        "data": TAG_CALLDATA
    }

    signed_tx = w3.eth.account.sign_transaction(tx, private_key=pk)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    tx_hex = tx_hash.hex()

    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=30)
    return {
        "success": receipt.status == 1,
        "network": cfg["name"],
        "tx_hash": f"0x{tx_hex}",
        "block": receipt.blockNumber,
        "explorer_url": f"{cfg['explorer']}{tx_hex}"
    }


def main():
    parser = argparse.ArgumentParser(description="A.GRID Multi-Chain Volume Daemon")
    parser.add_argument("--interval", type=int, default=180, help="Interval in seconds between settlements (default: 180s)")
    parser.add_argument("--iterations", type=int, default=5, help="Number of settlements to execute (default: 5, 0 for infinite)")
    args = parser.parse_args()

    wallet = load_wallet()
    print("=" * 80)
    print("🤖 [A.GRID MULTI-CHAIN ON-CHAIN VOLUME DAEMON]")
    print(f"• Bot Address      : {wallet['address']}")
    print(f"• Sovereign Treasury: {TREASURY_ADDRESS}")
    print(f"• Active Networks  : Base Mainnet & Arbitrum One")
    print(f"• Interval         : {args.interval}s")
    print("=" * 80)

    net_keys = ["base", "arbitrum"]
    count = 0
    try:
        while True:
            net_key = net_keys[count % len(net_keys)]
            t_now = time.strftime("%Y-%m-%d %H:%M:%S")
            print(f"\n[{t_now}] [Cycle #{count + 1}] Broadcasting micro-settlement to {NETWORKS[net_key]['name']}...")
            res = send_micro_toll(net_key, wallet)
            if res.get("success"):
                print(f"  ✅ SUCCESS on {res['network']} (Block: {res['block']})")
                print(f"  🔗 Explorer: {res['explorer_url']}")
            else:
                print(f"  ❌ FAILED: {res.get('error')}")

            count += 1
            if args.iterations > 0 and count >= args.iterations:
                print(f"\n✨ Completed requested {args.iterations} volume cycles.")
                break

            print(f"  ⏳ Sleeping {args.interval}s until next on-chain cycle...")
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\n🛑 Daemon stopped by user.")


if __name__ == "__main__":
    main()
