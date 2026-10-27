import os
import sys
import json
import time
import struct
import base64
import urllib.request
from cryptography.hazmat.primitives.asymmetric import ed25519

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"

def b58encode(v: bytes) -> str:
    n = int.from_bytes(v, "big")
    chars = []
    while n > 0:
        n, r = divmod(n, 58)
        chars.append(ALPHABET[r])
    res = "".join(reversed(chars))
    pad = len(v) - len(v.lstrip(b"\x00"))
    return "1" * pad + res

def b58decode(v: str) -> bytes:
    n = 0
    for char in v:
        n = n * 58 + ALPHABET.index(char)
    res = n.to_bytes((n.bit_length() + 7) // 8, "big") if n > 0 else b""
    pad = len(v) - len(v.lstrip("1"))
    return b"\x00" * pad + res

SYSTEM_PROGRAM_ID = b58decode("11111111111111111111111111111111")
SOLANA_RPC = os.getenv("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com")
TREASURY_SOLANA = "411ksMz9RHYVtVMe6RUUErzZYtrU9zzvkgzswKbqx9qp"

def rpc_call(method: str, params: list):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode("utf-8")
    req = urllib.request.Request(SOLANA_RPC, data=body, headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=12) as r:
        return json.loads(r.read().decode("utf-8"))

def send_solana_micro_toll(lamports: int = 5000): # 0.000005 SOL
    with open("data/bot_wallet_solana.json") as f:
        wdata = json.load(f)

    sender_addr = wdata["address"]
    full_keypair_bytes = b58decode(wdata["private_key_b58"])
    priv_bytes = full_keypair_bytes[:32]
    pub_bytes = full_keypair_bytes[32:]

    # 1. Get recent blockhash
    res = rpc_call("getLatestBlockhash", [{"commitment": "finalized"}])
    blockhash_b58 = res["result"]["value"]["blockhash"]
    blockhash_bytes = b58decode(blockhash_b58)

    recipient_bytes = b58decode(TREASURY_SOLANA)

    # 2. Build Transaction
    accounts = [pub_bytes, recipient_bytes, SYSTEM_PROGRAM_ID]
    account_keys = b"".join(accounts)
    instruction_data = struct.pack("<IQ", 2, lamports) # SystemProgram.Transfer
    compiled_instruction = bytes([2, 2, 0, 1, len(instruction_data)]) + instruction_data
    header = bytes([1, 0, 1])
    message = header + bytes([3]) + account_keys + blockhash_bytes + bytes([1]) + compiled_instruction

    # 3. Sign
    priv_key = ed25519.Ed25519PrivateKey.from_private_bytes(priv_bytes)
    signature = priv_key.sign(message)

    # 4. Serialize wire transaction
    tx_bytes = bytes([1]) + signature + message
    tx_b64 = base64.b64encode(tx_bytes).decode("utf-8")

    # 5. Broadcast
    send_res = rpc_call("sendTransaction", [tx_b64, {"encoding": "base64"}])
    if "error" in send_res:
        return {"success": False, "error": send_res["error"]}
    
    tx_sig = send_res["result"]
    return {
        "success": True,
        "signature": tx_sig,
        "solscan_url": f"https://solscan.io/tx/{tx_sig}",
        "lamports": lamports
    }

if __name__ == "__main__":
    with open("data/bot_wallet_solana.json") as f:
        wdata = json.load(f)
    print("=== SOLANA BOT STATUS ===")
    print("Bot Address:", wdata["address"])
    bal_res = rpc_call("getBalance", [wdata["address"]])
    lamports = bal_res.get("result", {}).get("value", 0)
    print(f"Balance: {lamports / 1e9} SOL ({lamports} lamports)")
    if lamports > 5000:
        print("Broadcasting live Solana micro-toll...")
        result = send_solana_micro_toll()
        print("Result:", result)
    else:
        print("Notice: Awaiting SOL deposit to broadcast live transaction.")
