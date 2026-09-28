import os
import sys
from web3 import Web3
from eth_account import Account
from dotenv import load_dotenv
from eth_abi import encode

# Set UTF-8 encoding for stdout
sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()

SAFE_ADDRESS = "0x06db5A847F24d0feC5151a01937700E221d55e19"
DEPLOYER_KEY = os.getenv("DEPLOYER_PRIVATE_KEY")
RPC_URL = "https://polygon-bor-rpc.publicnode.com"

w3 = Web3(Web3.HTTPProvider(RPC_URL))
account = Account.from_key(DEPLOYER_KEY)

tx_hash = "12d0821887d4104dc65968248bcdff45dc8a9ea0d8c261c85ad173366bb331d5"
receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
new_guard_address = receipt.contractAddress
print(f"[SUCCESS] SafeSecurityGateGuard deployed at: {new_guard_address}")

# Verify supportsInterface
supports_call = w3.eth.call({
    "to": new_guard_address,
    "data": "0x01ffc9a7e6d7a83a00000000000000000000000000000000000000000000000000000000"
})
print(f"supportsInterface(0xe6d7a83a): {supports_call.hex()} (Expected: ...0001)")

# Step 2: Set guard on Safe
safe_nonce = int.from_bytes(w3.eth.call({"to": SAFE_ADDRESS, "data": bytes.fromhex("affed0e0")}), 'big')
print(f"Safe Nonce: {safe_nonce}")

set_guard_calldata = bytes.fromhex("e19a9dd9") + encode(["address"], [new_guard_address])

# getTransactionHash
get_tx_hash_sel = bytes.fromhex("d8d11f78")
args = encode(
    ["address", "uint256", "bytes", "uint8", "uint256", "uint256", "uint256", "address", "address", "uint256"],
    [
        SAFE_ADDRESS,
        0,
        set_guard_calldata,
        0,
        0,
        0,
        0,
        "0x0000000000000000000000000000000000000000",
        "0x0000000000000000000000000000000000000000",
        safe_nonce
    ]
)
safe_tx_hash = w3.eth.call({"to": SAFE_ADDRESS, "data": get_tx_hash_sel + args})
print(f"SafeTxHash: {safe_tx_hash.hex()}")

# Owner signs SafeTxHash
signed_safe_tx = Account._sign_hash(safe_tx_hash, account.key)
sig_bytes = signed_safe_tx.signature

# Prepare execTransaction call
exec_selector = bytes.fromhex("6a761202")
exec_args = encode(
    ["address", "uint256", "bytes", "uint8", "uint256", "uint256", "uint256", "address", "address", "bytes"],
    [
        SAFE_ADDRESS,
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

# Test eth_call simulation first
print("Testing eth_call simulation of execTransaction...")
sim_res = w3.eth.call({
    "from": account.address,
    "to": SAFE_ADDRESS,
    "data": exec_calldata
})
print(f"Simulation result: {sim_res.hex()} (SUCCESS!)")

# Send the real transaction to attach Guard!
deployer_nonce = w3.eth.get_transaction_count(account.address, "pending")
gas_price = int(w3.eth.gas_price * 1.3)

safe_exec_tx = {
    "from": account.address,
    "to": SAFE_ADDRESS,
    "data": exec_calldata,
    "nonce": deployer_nonce,
    "gasPrice": gas_price,
    "chainId": 137
}

gas_limit = w3.eth.estimate_gas(safe_exec_tx)
safe_exec_tx["gas"] = int(gas_limit * 1.3)

signed_exec = account.sign_transaction(safe_exec_tx)
exec_tx_hash = w3.eth.send_raw_transaction(signed_exec.raw_transaction)
print(f"Sent execTransaction to setGuard! Tx Hash: {exec_tx_hash.hex()}")
print("Waiting for receipt...")

exec_receipt = w3.eth.wait_for_transaction_receipt(exec_tx_hash, timeout=120)
print(f"Receipt status: {exec_receipt.status} (1 = SUCCESS!)")

# Final verification
guard_slot = "0x4a204f620c8c5ccdca3fd54d003b799ba82d82afd266163c202d2d86c244ddc0"
slot_g = w3.eth.get_storage_at(SAFE_ADDRESS, guard_slot)
decoded_guard = "0x" + slot_g.hex()[-40:]
print(f"\n==================================================")
print(f"TARGET SAFE: {SAFE_ADDRESS}")
print(f"CURRENT ACTIVE GUARD ON-CHAIN: {decoded_guard}")
print(f"NEW GUARD ADDRESS:             {new_guard_address}")
print(f"SUCCESSFULLY ATTACHED: {decoded_guard.lower() == new_guard_address.lower()}")
print(f"==================================================")
