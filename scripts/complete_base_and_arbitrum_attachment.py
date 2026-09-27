import os
import sys
import time
import json
from web3 import Web3
from eth_account import Account
from dotenv import load_dotenv
from eth_abi import encode

sys.stdout.reconfigure(encoding='utf-8')
load_dotenv()

DEPLOYER_KEY = os.getenv("DEPLOYER_PRIVATE_KEY")
DEPLOYER = "0x255F9991233f86B29dB847c8d5b8CB9915e80dCf"

# Safe v1.3.0 Canonical Addresses across EVM L2s
FACTORY = "0xa6B71E26C5e0845f74c812102Ca7114b6a896AB2"
SINGLETON = "0x3E5c63644E683549055b9Be8653de26E0B4CD36E" # SafeL2 v1.3.0
FALLBACK_HANDLER = "0xf48f2B2d2a534e402487b3ee7C18c33Aec0Fe5e4"
GUARD_SLOT = "0x4a204f620c8c5ccdca3fd54d003b799ba82d82afd266163c202d2d86c244ddc0"

# Deployed Upgraded Guards with ERC-165 (supportsInterface)
BASE_GUARD = "0xb44Bc2Acdd156cE08b549A00a3102e4B01276654"
BASE_SAFE = "0x81fB233670dDe83eb87022fF40A3868dCF0AAfE7"

ARB_GUARD = "0x835D01534A5d2E63D52636FAFB1019F889D1E66B"

print("=== FINALIZING BASE & ARBITRUM SAFE GUARD ATTACHMENT ===")

account = Account.from_key(DEPLOYER_KEY)

# =========================================================================
# 1. BASE: Attach Guard to Existing Base Safe
# =========================================================================
print("\n" + "=" * 60)
print("🔵 1. BASE MAINNET: ATTACHING GUARD TO SAFE")
print("=" * 60)
w3_base = Web3(Web3.HTTPProvider("https://mainnet.base.org", request_kwargs={"headers": {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}, "timeout": 30}))
print(f"Base Deployer Balance: {w3_base.from_wei(w3_base.eth.get_balance(DEPLOYER), 'ether'):.6f} ETH")

base_nonce = int.from_bytes(w3_base.eth.call({"to": BASE_SAFE, "data": bytes.fromhex("affed0e0")}), 'big')
print(f"Base Safe Nonce: {base_nonce}")

set_guard_calldata = bytes.fromhex("e19a9dd9") + encode(["address"], [BASE_GUARD])
r = bytes.fromhex(DEPLOYER[2:].lower().rjust(64, '0'))
s = bytes(32)
v = bytes([1])
sig_bytes = r + s + v

exec_sel = bytes.fromhex("6a761202")
exec_args = encode(
    ["address", "uint256", "bytes", "uint8", "uint256", "uint256", "uint256", "address", "address", "bytes"],
    [
        BASE_SAFE,
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

nonce_tx = w3_base.eth.get_transaction_count(DEPLOYER, "pending")
gas_price = int(w3_base.eth.gas_price * 1.5)

base_attach_tx = {
    "from": DEPLOYER,
    "to": BASE_SAFE,
    "data": exec_sel + exec_args,
    "nonce": nonce_tx,
    "gasPrice": gas_price,
    "gas": 150000,
    "chainId": 8453
}
signed_base_attach = account.sign_transaction(base_attach_tx)
base_attach_tx_hash = w3_base.eth.send_raw_transaction(signed_base_attach.raw_transaction)
print(f"Base Attach Guard Tx Hash: {base_attach_tx_hash.hex()}")
base_attach_rc = w3_base.eth.wait_for_transaction_receipt(base_attach_tx_hash, timeout=120)
print(f"Base Attach Receipt Status: {base_attach_rc.status} (Gas: {base_attach_rc.gasUsed})")

base_slot = w3_base.eth.get_storage_at(BASE_SAFE, GUARD_SLOT)
base_active_guard = "0x" + base_slot.hex()[-40:]
print(f"Base Active Guard in Storage: {base_active_guard}")
print(f"Base Guard Status: {'PERFECTLY ATTACHED & ACTIVE!' if base_active_guard.lower() == BASE_GUARD.lower() else 'FAILED'}")


# =========================================================================
# 2. ARBITRUM: Deploy Safe & Attach Guard
# =========================================================================
print("\n" + "=" * 60)
print("🟠 2. ARBITRUM ONE: CREATING SAFE & ATTACHING GUARD")
print("=" * 60)
w3_arb = Web3(Web3.HTTPProvider("https://arb1.arbitrum.io/rpc", request_kwargs={"headers": {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}, "timeout": 30}))
print(f"Arbitrum Deployer Balance: {w3_arb.from_wei(w3_arb.eth.get_balance(DEPLOYER), 'ether'):.6f} ETH")

# Setup calldata
setup_sel = bytes.fromhex("b63e800d")
setup_args = encode(
    ["address[]", "uint256", "address", "bytes", "address", "address", "uint256", "address"],
    [
        [DEPLOYER],
        1,
        "0x0000000000000000000000000000000000000000",
        b"",
        FALLBACK_HANDLER,
        "0x0000000000000000000000000000000000000000",
        0,
        "0x0000000000000000000000000000000000000000"
    ]
)
initializer = setup_sel + setup_args

create_sel = bytes.fromhex("1688f0b9")
salt_nonce = int(time.time())
create_args = encode(["address", "bytes", "uint256"], [SINGLETON, initializer, salt_nonce])
factory_calldata = create_sel + create_args

nonce_tx = w3_arb.eth.get_transaction_count(DEPLOYER, "pending")
gas_price = int(w3_arb.eth.gas_price * 1.5)

arb_create_tx = {
    "from": DEPLOYER,
    "to": FACTORY,
    "data": factory_calldata,
    "nonce": nonce_tx,
    "gasPrice": gas_price,
    "gas": 400000,
    "chainId": 42161
}
signed_arb_create = account.sign_transaction(arb_create_tx)
arb_create_tx_hash = w3_arb.eth.send_raw_transaction(signed_arb_create.raw_transaction)
print(f"Arbitrum Safe Creation Tx Hash: {arb_create_tx_hash.hex()}")
arb_create_rc = w3_arb.eth.wait_for_transaction_receipt(arb_create_tx_hash, timeout=120)

new_arb_safe = None
for log in arb_create_rc.logs:
    if log.address.lower() == FACTORY.lower() and len(log.data) >= 32:
        new_arb_safe = "0x" + log.data[:32].hex()[-40:]
        break
if not new_arb_safe:
    new_arb_safe = "0x" + arb_create_rc.logs[0].data[:32].hex()[-40:]

new_arb_safe = w3_arb.to_checksum_address(new_arb_safe)
print(f"Arbitrum Safe Created At: {new_arb_safe} (Gas: {arb_create_rc.gasUsed})")

# Attach Guard on Arbitrum
set_guard_calldata_arb = bytes.fromhex("e19a9dd9") + encode(["address"], [ARB_GUARD])
exec_args_arb = encode(
    ["address", "uint256", "bytes", "uint8", "uint256", "uint256", "uint256", "address", "address", "bytes"],
    [
        new_arb_safe,
        0,
        set_guard_calldata_arb,
        0,
        0,
        0,
        0,
        "0x0000000000000000000000000000000000000000",
        "0x0000000000000000000000000000000000000000",
        sig_bytes
    ]
)

nonce_tx = w3_arb.eth.get_transaction_count(DEPLOYER, "pending")
gas_price = int(w3_arb.eth.gas_price * 1.5)

arb_attach_tx = {
    "from": DEPLOYER,
    "to": new_arb_safe,
    "data": exec_sel + exec_args_arb,
    "nonce": nonce_tx,
    "gasPrice": gas_price,
    "gas": 250000,
    "chainId": 42161
}
signed_arb_attach = account.sign_transaction(arb_attach_tx)
arb_attach_tx_hash = w3_arb.eth.send_raw_transaction(signed_arb_attach.raw_transaction)
print(f"Arbitrum Attach Guard Tx Hash: {arb_attach_tx_hash.hex()}")
arb_attach_rc = w3_arb.eth.wait_for_transaction_receipt(arb_attach_tx_hash, timeout=120)
print(f"Arbitrum Attach Receipt Status: {arb_attach_rc.status} (Gas: {arb_attach_rc.gasUsed})")

arb_slot = w3_arb.eth.get_storage_at(new_arb_safe, GUARD_SLOT)
arb_active_guard = "0x" + arb_slot.hex()[-40:]
print(f"Arbitrum Active Guard in Storage: {arb_active_guard}")
print(f"Arbitrum Guard Status: {'PERFECTLY ATTACHED & ACTIVE!' if arb_active_guard.lower() == ARB_GUARD.lower() else 'FAILED'}")

print("\n" + "=" * 60)
print("🎉 MULTI-CHAIN SUMMARY:")
print(f"Polygon Safe:  0x06db5A847F24d0feC5151a01937700E221d55e19 | Guard: 0x8c2a8B9Ff05a92ad16E0ED58ac83aD6C11cb18Cb (ACTIVE)")
print(f"Base Safe:     {BASE_SAFE} | Guard: {BASE_GUARD} ({'ACTIVE' if base_active_guard.lower() == BASE_GUARD.lower() else 'FAILED'})")
print(f"Arbitrum Safe: {new_arb_safe} | Guard: {ARB_GUARD} ({'ACTIVE' if arb_active_guard.lower() == ARB_GUARD.lower() else 'FAILED'})")
print("=" * 60)
