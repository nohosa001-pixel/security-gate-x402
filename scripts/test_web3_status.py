import json
import sys
from web3 import Web3

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

with open("data/bot_wallet_evm.json") as f:
    wdata = json.load(f)

w3_base = Web3(Web3.HTTPProvider("https://mainnet.base.org"))
w3_arb = Web3(Web3.HTTPProvider("https://arb1.arbitrum.io/rpc"))

addr = wdata["address"]
pk = wdata["private_key"]

base_bal = w3_base.eth.get_balance(addr)
arb_bal = w3_arb.eth.get_balance(addr)

base_gas_price = w3_base.eth.gas_price
arb_gas_price = w3_arb.eth.gas_price

print("=== ONCHAIN STATUS ===")
print("Bot Address:", addr)
print(f"Base Balance: {w3_base.from_wei(base_bal, 'ether')} ETH")
print(f"Base Gas Price: {w3_base.from_wei(base_gas_price, 'gwei')} Gwei")
print(f"Arbitrum Balance: {w3_arb.from_wei(arb_bal, 'ether')} ETH")
print(f"Arbitrum Gas Price: {w3_arb.from_wei(arb_gas_price, 'gwei')} Gwei")
