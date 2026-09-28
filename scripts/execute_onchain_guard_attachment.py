import os
import sys
from web3 import Web3
from dotenv import load_dotenv
from eth_abi import encode
from eth_account import Account

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()

SAFE = "0x06db5A847F24d0feC5151a01937700E221d55e19"
GUARD = "0x8c2a8B9Ff05a92ad16E0ED58ac83aD6C11cb18Cb"
DEPLOYER_KEY = os.getenv("DEPLOYER_PRIVATE_KEY")
RPC_URL = "https://polygon-bor-rpc.publicnode.com"

w3 = Web3(Web3.HTTPProvider(RPC_URL, request_kwargs={"headers": {"User-Agent": "Mozilla/5.0"}, "timeout": 30}))
account = Account.from_key(DEPLOYER_KEY)

print("=" * 60)
print("🚀 ATTACHING SAFESECURITYGATEGUARD TO SAFE WALLET ON POLYGON")
print(f"Safe Address:    {SAFE}")
print(f"New Guard:       {GUARD}")
print(f"Owner Address:   {account.address}")
print(f"Owner Balance:   {w3.from_wei(w3.eth.get_balance(account.address), 'ether')} POL")
print("=" * 60)

# 1. Fetch current safe nonce
safe_nonce = int.from_bytes(w3.eth.call({"to": SAFE, "data": bytes.fromhex("affed0e0")}), 'big')
print(f"Current Safe Nonce: {safe_nonce}")

# 2. Calldata for setGuard(GUARD)
set_guard_calldata = bytes.fromhex("e19a9dd9") + encode(["address"], [GUARD])

# 3. SafeTx pre-validated signature (v=1, r=owner, s=0)
r = bytes.fromhex(account.address[2:].lower().rjust(64, '0'))
s = bytes(32)
v = bytes([1])
sig_bytes = r + s + v

# 4. Calldata for execTransaction
exec_selector = bytes.fromhex("6a761202")
exec_args = encode(
    ["address", "uint256", "bytes", "uint8", "uint256", "uint256", "uint256", "address", "address", "bytes"],
    [
        SAFE,
        0,
        set_guard_calldata,
        0,
        0,
        0,
        0,
        "0x0000000000000000000000000000000000000000",
        "0x0000000000000000000000000000000000000000",
        sig_bytes
    ]
)
exec_calldata = exec_selector + exec_args

# 5. Build and send transaction
nonce = w3.eth.get_transaction_count(account.address, "pending")
network_gas_price = w3.eth.gas_price
gas_price = max(int(network_gas_price * 1.5), 45000000000)

tx = {
    "from": account.address,
    "to": SAFE,
    "data": exec_calldata,
    "nonce": nonce,
    "gasPrice": gas_price,
    "chainId": 137
}

gas_est = w3.eth.estimate_gas(tx)
tx["gas"] = int(gas_est * 1.3)
print(f"Gas Estimate: {gas_est} -> Set Gas Limit: {tx['gas']}, Gas Price: {gas_price // 10**9} Gwei")

signed_tx = account.sign_transaction(tx)
tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
print(f"\nBroadcasted setGuard Transaction! Tx Hash: {tx_hash.hex()}")
print("Waiting for Polygon block confirmation...")

receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
print(f"Receipt Status: {receipt.status} (1 = SUCCESS!)")
print(f"Block Number:   {receipt.blockNumber}")
print(f"Gas Used:       {receipt.gasUsed}")

# 6. Verify On-Chain Guard Storage Slot
# keccak256("guard_manager.guard.address") = 0x4a204f620c8c5ccdca3fd54d003badd85ba500436a431f0cbda4f558c93c34c8
guard_slot = "0x4a204f620c8c5ccdca3fd54d003badd85ba500436a431f0cbda4f558c93c34c8"
slot_g = w3.eth.get_storage_at(SAFE, guard_slot)
decoded_guard = "0x" + slot_g.hex()[-40:]

print("\n" + "=" * 60)
print(f"FINAL ON-CHAIN VERIFICATION RESULT:")
print(f"Active Guard Slot: {slot_g.hex()}")
print(f"Active Guard Address: {decoded_guard}")
print(f"Expected Guard Address: {GUARD}")
print(f"STATUS: {'PERFECTLY ATTACHED & ACTIVE!' if decoded_guard.lower() == GUARD.lower() else 'FAILED'}")
print("=" * 60)
