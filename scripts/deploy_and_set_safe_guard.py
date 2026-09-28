import os
import sys
import json
import solcx
from web3 import Web3
from eth_account import Account
from dotenv import load_dotenv
from eth_abi import encode

# Ensure clean UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()

SAFE_ADDRESS = "0x06db5A847F24d0feC5151a01937700E221d55e19"
DEPLOYER_KEY = os.getenv("DEPLOYER_PRIVATE_KEY")
RPC_URL = "https://polygon-bor-rpc.publicnode.com"

w3 = Web3(Web3.HTTPProvider(RPC_URL, request_kwargs={"timeout": 30}))
account = Account.from_key(DEPLOYER_KEY)

print(f"=== DEPLOY & ATTACH COMPLIANT SAFE GUARD ===")
print(f"Deployer Account: {account.address}")
print(f"Deployer POL Balance: {w3.from_wei(w3.eth.get_balance(account.address), 'ether')} POL")
print(f"Target Safe: {SAFE_ADDRESS}")

# 1. Compile SafeSecurityGateGuard.sol
contract_path = os.path.join(os.path.dirname(__file__), "..", "contracts", "SafeSecurityGateGuard.sol")
print(f"\nCompiling {contract_path}...")
solcx.install_solc("0.8.20")
compiled = solcx.compile_files(
    [contract_path],
    solc_version="0.8.20",
    output_values=["abi", "bin"]
)

# Find contract key
guard_key = [k for k in compiled.keys() if k.endswith(":SafeSecurityGateGuard")][0]
contract_data = compiled[guard_key]
abi = contract_data["abi"]
bytecode = contract_data["bin"]
print(f"Bytecode length: {len(bytecode)} characters")

# 2. Deploy SafeSecurityGateGuard
oracle_signer = "0x255F9991233f86B29dB847c8d5b8CB9915e80dCf"
max_risk = 30

contract = w3.eth.contract(abi=abi, bytecode=bytecode)
nonce = w3.eth.get_transaction_count(account.address, "pending")
network_gas_price = w3.eth.gas_price
gas_price = max(int(network_gas_price * 1.4), 40000000000) # >= 40 Gwei

print(f"Building deployment tx (nonce={nonce}, gasPrice={gas_price // 10**9} Gwei)...")
tx = contract.constructor(oracle_signer, max_risk).build_transaction({
    "from": account.address,
    "nonce": nonce,
    "gasPrice": gas_price,
    "chainId": 137
})

gas_est = w3.eth.estimate_gas(tx)
tx["gas"] = int(gas_est * 1.25)
print(f"Estimated Gas: {gas_est} -> Set Gas: {tx['gas']}")

signed_tx = account.sign_transaction(tx)
tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
print(f"Deploy Tx Broadcasted! TxHash: {tx_hash.hex()}")
print("Waiting for block confirmation on Polygon...")

receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
new_guard_address = receipt.contractAddress
print(f"[SUCCESS] Upgraded SafeSecurityGateGuard deployed at: {new_guard_address}")

# Verify code length & supportsInterface
code = w3.eth.get_code(new_guard_address)
print(f"Verified on-chain code length: {len(code)} bytes")

# Check supportsInterface(0xe6d7a83a)
supports_calldata = bytes.fromhex("01ffc9a7") + encode(["bytes4"], [bytes.fromhex("e6d7a83a")])
supports_res = w3.eth.call({"to": new_guard_address, "data": supports_calldata})
is_supported = bool(int.from_bytes(supports_res, 'big'))
print(f"supportsInterface(0xe6d7a83a) returned: {is_supported}")

# 3. Attach Guard to Safe via execTransaction
print(f"\n[Step 2] Attaching Guard to Safe {SAFE_ADDRESS}...")
safe_nonce = int.from_bytes(w3.eth.call({"to": SAFE_ADDRESS, "data": bytes.fromhex("affed0e0")}), 'big')
print(f"Current Safe Nonce: {safe_nonce}")

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

# Test eth_call simulation
print("Testing eth_call simulation of execTransaction...")
sim_res = w3.eth.call({
    "from": account.address,
    "to": SAFE_ADDRESS,
    "data": exec_calldata
})
print(f"Simulation result: {sim_res.hex()} (SUCCESS!)")

# Send the real transaction to attach Guard!
deployer_nonce = w3.eth.get_transaction_count(account.address, "pending")
network_gas_price = w3.eth.gas_price
gas_price = max(int(network_gas_price * 1.4), 40000000000)

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
print("Waiting for on-chain receipt...")

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
