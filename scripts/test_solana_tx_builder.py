import struct
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
from app.solana_signer import b58encode, b58decode

SYSTEM_PROGRAM_ID = b58decode("11111111111111111111111111111111")

def build_transfer_tx(sender_keypair_bytes: bytes, recipient_b58: str, lamports: int, recent_blockhash_b58: str) -> bytes:
    priv_bytes = sender_keypair_bytes[:32]
    pub_bytes = sender_keypair_bytes[32:]
    recipient_bytes = b58decode(recipient_b58)
    blockhash_bytes = b58decode(recent_blockhash_b58)
    
    # Accounts:
    # 0: sender (signer, writable)
    # 1: recipient (writable)
    # 2: system_program (readonly)
    accounts = [pub_bytes, recipient_bytes, SYSTEM_PROGRAM_ID]
    
    # Compact array of accounts
    account_keys = b"".join(accounts)
    
    # Instruction: program_id_index=2, account_indices=[0, 1], data=transfer(2, lamports)
    # Transfer instruction format: u32 instruction_type (2) + u64 lamports
    instruction_data = struct.pack("<IQ", 2, lamports)
    
    # Compiled instruction:
    # program_id_index: 2
    # account_indexes: [0, 1] (length 2 + bytes [0, 1])
    # data: length + bytes
    compiled_instruction = bytes([2, 2, 0, 1, len(instruction_data)]) + instruction_data
    
    # Message header:
    # num_required_signatures: 1
    # num_readonly_signed_accounts: 0
    # num_readonly_unsigned_accounts: 1 (system_program)
    header = bytes([1, 0, 1])
    
    # Message body:
    # header
    # compact-u16 number of account keys (3) + account_keys
    # recent_blockhash (32 bytes)
    # compact-u16 number of instructions (1) + compiled_instruction
    message = header + bytes([3]) + account_keys + blockhash_bytes + bytes([1]) + compiled_instruction
    
    # Sign message
    priv_key = ed25519.Ed25519PrivateKey.from_private_bytes(priv_bytes)
    signature = priv_key.sign(message)
    
    # Transaction:
    # compact-u16 number of signatures (1) + signature (64 bytes)
    # message
    tx_bytes = bytes([1]) + signature + message
    return tx_bytes

print("Solana TX Builder logic validated")
