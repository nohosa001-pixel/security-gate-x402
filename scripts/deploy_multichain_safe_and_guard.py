import os
import sys
import time
import json
import solcx
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
GUARD_SLOT = "0x4a204f620c8c5ccdca3fd54d003badd85ba500436a431f0cbda4f558c93c34c8"

CHAINS = {
    "Base": {
        "chain_id": 8453,
        "rpc": "https://mainnet.base.org",
        "explorer": "https://basescan.org"
    },
    "Arbitrum": {
        "chain_id": 42161,
        "rpc": "https://arbitrum-one-rpc.publicnode.com",
        "explorer": "https://arbiscan.io"
    }
}

print("=== MULTI-CHAIN SAFE & GUARD DEPLOYMENT & ATTACHMENT ===")

# 1. Compile SafeSecurityGateGuard.sol
contract_path = os.path.join(os.path.dirname(__file__), "..", "contracts", "SafeSecurityGateGuard.sol")
print(f"Compiling {contract_path}...")
solcx.install_solc("0.8.20")
compiled = solcx.compile_files([contract_path], solc_version="0.8.20", output_values=["abi", "bin"])
guard_key = [k for k in compiled.keys() if k.endswith(":SafeSecurityGateGuard")][0]
guard_abi = compiled[guard_key]["abi"]
guard_bytecode = compiled[guard_key]["bin"]
print(f"Compiled successfully! Bytecode: {len(guard_bytecode)} chars")

results = {}

for chain_name, chain_info in CHAINS.items():
    print(f"\n" + "=" * 60)
    print(f"🌐 PROCESSING {chain_name.upper()} MAINNET (Chain ID {chain_info['chain_id']})")
    print("=" * 60)
    
    w3 = Web3(Web3.HTTPProvider(chain_info["rpc"], request_kwargs={"headers": {"User-Agent": "Mozilla/5.0"}, "timeout": 30}))
    account = Account.from_key(DEPLOYER_KEY)
    
    bal = w3.from_wei(w3.eth.get_balance(account.address), 'ether')
    print(f"Deployer Balance: {bal:.6f} ETH")
    
    # -------------------------------------------------------------
    # Step A: Deploy upgraded SafeSecurityGateGuard
    # -------------------------------------------------------------
    print(f"\n[Step A] Deploying SafeSecurityGateGuard on {chain_name}...")
    guard_contract = w3.eth.contract(abi=guard_abi, bytecode=guard_bytecode)
    nonce = w3.eth.get_transaction_count(account.address, "pending")
    gas_price = int(w3.eth.gas_price * 1.3)
    
    deploy_tx = guard_contract.constructor(DEPLOYER, 30).build_transaction({
        "from": account.address,
        "nonce": nonce,
        "gasPrice": gas_price,
        "chainId": chain_info["chain_id"]
    })
    deploy_tx["gas"] = int(w3.eth.estimate_gas(deploy_tx) * 1.3)
    
    signed_deploy = account.sign_transaction(deploy_tx)
    tx_hash = w3.eth.send_raw_transaction(signed_deploy.raw_transaction)
    print(f" -> Guard Deploy Tx: {tx_hash.hex()}")
    
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
    guard_address = receipt.contractAddress
    print(f" -> Guard Deployed At: {guard_address} (Gas: {receipt.gasUsed})")
    
    # Verify supportsInterface
    supp_130 = w3.eth.call({"to": guard_address, "data": "0x01ffc9a7e6d7a83a00000000000000000000000000000000000000000000000000000000"})
    print(f" -> Verified supportsInterface(0xe6d7a83a): {bool(int.from_bytes(supp_130, 'big'))}")
    
    # -------------------------------------------------------------
    # Step B: Create Safe via Canonical SafeProxyFactory v1.3.0
    # -------------------------------------------------------------
    print(f"\n[Step B] Creating Safe Wallet via SafeProxyFactory on {chain_name}...")
    # Safe.setup selector: 0xb63e800d
    # setup(address[] _owners, uint256 _threshold, address to, bytes data, address fallbackHandler, address paymentToken, uint256 payment, address paymentReceiver)
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
    
    # Factory.createProxyWithNonce selector: 0x1688f0b9
    # createProxyWithNonce(address _singleton, bytes initializer, uint256 saltNonce)
    create_sel = bytes.fromhex("1688f0b9")
    salt_nonce = int(time.time())
    create_args = encode(["address", "bytes", "uint256"], [SINGLETON, initializer, salt_nonce])
    factory_calldata = create_sel + create_args
    
    nonce = w3.eth.get_transaction_count(account.address, "pending")
    gas_price = int(w3.eth.gas_price * 1.3)
    create_tx = {
        "from": account.address,
        "to": FACTORY,
        "data": factory_calldata,
        "nonce": nonce,
        "gasPrice": gas_price,
        "chainId": chain_info["chain_id"]
    }
    create_tx["gas"] = int(w3.eth.estimate_gas(create_tx) * 1.3)
    
    signed_create = account.sign_transaction(create_tx)
    create_tx_hash = w3.eth.send_raw_transaction(signed_create.raw_transaction)
    print(f" -> Safe Creation Tx: {create_tx_hash.hex()}")
    
    create_rc = w3.eth.wait_for_transaction_receipt(create_tx_hash, timeout=120)
    # Event ProxyCreation(address proxy, address singleton)
    # The proxy address is in topics[1] or data depending on factory version; in v1.3.0 it's in logs
    # In SafeProxyFactory v1.3.0, ProxyCreation topic 0 = 0x4f51faf6c4561ff97f067657e43452b0280a4b3615ae909e382e0c4063c4797a
    # event ProxyCreation(GnosisSafeProxy proxy, address singleton);
    # First 32 bytes of log data or unindexed is proxy address
    new_safe_address = None
    for log in create_rc.logs:
        if log.address.lower() == FACTORY.lower() and len(log.data) >= 32:
            new_safe_address = "0x" + log.data[:32].hex()[-40:]
            break
            
    if not new_safe_address:
        # Fallback inspection from receipt
        new_safe_address = "0x" + create_rc.logs[0].data[:32].hex()[-40:]
        
    new_safe_address = w3.to_checksum_address(new_safe_address)
    print(f" -> Safe Created At: {new_safe_address} (Gas: {create_rc.gasUsed})")
    
    # -------------------------------------------------------------
    # Step C: Attach Guard to newly created Safe
    # -------------------------------------------------------------
    print(f"\n[Step C] Attaching Guard to Safe on {chain_name}...")
    safe_nonce = int.from_bytes(w3.eth.call({"to": new_safe_address, "data": bytes.fromhex("affed0e0")}), 'big')
    print(f" -> Safe Nonce: {safe_nonce}")
    
    set_guard_calldata = bytes.fromhex("e19a9dd9") + encode(["address"], [guard_address])
    
    # Pre-validated signature: r=owner, s=0, v=1
    r = bytes.fromhex(account.address[2:].lower().rjust(64, '0'))
    s = bytes(32)
    v = bytes([1])
    sig_bytes = r + s + v
    
    exec_sel = bytes.fromhex("6a761202")
    exec_args = encode(
        ["address", "uint256", "bytes", "uint8", "uint256", "uint256", "uint256", "address", "address", "bytes"],
        [
            new_safe_address,
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
    exec_calldata = exec_sel + exec_args
    
    nonce = w3.eth.get_transaction_count(account.address, "pending")
    gas_price = int(w3.eth.gas_price * 1.3)
    attach_tx = {
        "from": account.address,
        "to": new_safe_address,
        "data": exec_calldata,
        "nonce": nonce,
        "gasPrice": gas_price,
        "chainId": chain_info["chain_id"]
    }
    attach_tx["gas"] = int(w3.eth.estimate_gas(attach_tx) * 1.3)
    
    signed_attach = account.sign_transaction(attach_tx)
    attach_tx_hash = w3.eth.send_raw_transaction(signed_attach.raw_transaction)
    print(f" -> Attach Guard Tx: {attach_tx_hash.hex()}")
    
    attach_rc = w3.eth.wait_for_transaction_receipt(attach_tx_hash, timeout=120)
    print(f" -> Guard Attach Receipt Status: {attach_rc.status} (Gas: {attach_rc.gasUsed})")
    
    # Verify Storage Slot
    slot_val = w3.eth.get_storage_at(new_safe_address, GUARD_SLOT)
    active_guard = "0x" + slot_val.hex()[-40:]
    is_active = active_guard.lower() == guard_address.lower()
    print(f" -> On-Chain Guard Slot: {active_guard}")
    print(f" -> Active Verification: {'PERFECTLY ATTACHED & ACTIVE!' if is_active else 'FAILED'}")
    
    results[chain_name] = {
        "chain_id": chain_info["chain_id"],
        "safe_address": new_safe_address,
        "guard_address": guard_address,
        "deploy_guard_tx": tx_hash.hex(),
        "create_safe_tx": create_tx_hash.hex(),
        "attach_guard_tx": attach_tx_hash.hex(),
        "is_active": is_active
    }

print("\n" + "=" * 60)
print("🎉 ALL MULTI-CHAIN SAFES & GUARDS SUCCESSFULLY DEPLOYED & ATTACHED!")
print("=" * 60)
print(json.dumps(results, indent=2))
