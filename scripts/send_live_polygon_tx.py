import json
import sys
import time
from web3 import Web3

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

with open("data/bot_wallet_evm.json") as f:
    wdata = json.load(f)

w3 = Web3(Web3.HTTPProvider("https://polygon-bor-rpc.publicnode.com"))
assert w3.is_connected(), "Failed to connect to Polygon RPC"

addr = wdata["address"]
pk = wdata["private_key"]
treasury_addr = "0xA185B43fDD19619f99952AAed6eabf1029bF36a1"

nonce = w3.eth.get_transaction_count(addr)
gas_price = w3.eth.gas_price

print(f"📡 Sending Live Polygon Micro-Toll from {addr} to Sovereign Treasury {treasury_addr}...")
print(f"Nonce: {nonce}, Gas Price: {w3.from_wei(gas_price, 'gwei')} Gwei")

tx = {
    "to": treasury_addr,
    "value": w3.to_wei(0.001, "ether"), # 0.001 POL micro-toll
    "gas": 40000,
    "gasPrice": int(gas_price * 1.3),
    "nonce": nonce,
    "chainId": 137,
    "data": "0x783430325f70726f746f636f6c5f746f6c6c" # "x402_protocol_toll"
}

signed_tx = w3.eth.account.sign_transaction(tx, private_key=pk)
tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)

print(f"🚀 TX Broadcasted! Hash: 0x{tx_hash.hex()}")
receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=30)
print(f"✅ Confirmed on Polygon Block: {receipt.blockNumber} (Status: {receipt.status})")
print(f"🔗 PolygonScan URL: https://polygonscan.com/tx/0x{tx_hash.hex()}")
