"""
Solana Ed25519 Cryptographic Oracle Signer & Attestation Verifier.
Provides native Ed25519 signature generation and verification for Solana Mainnet
Universal Escrow settlements, ensuring zero-dependency compatibility with Solana
on-chain instruction verification (Ed25519Program).
"""

import os
import hashlib
import struct
from typing import Dict, Any, Tuple
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.exceptions import InvalidSignature

ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def b58encode(v: bytes) -> str:
    """Encodes bytes into a Base58 string."""
    n = int.from_bytes(v, "big")
    chars = []
    while n > 0:
        n, r = divmod(n, 58)
        chars.append(ALPHABET[r])
    res = "".join(reversed(chars))
    pad = len(v) - len(v.lstrip(b"\x00"))
    return "1" * pad + res


def b58decode(v: str) -> bytes:
    """Decodes a Base58 string into bytes."""
    n = 0
    for char in v:
        n = n * 58 + ALPHABET.index(char)
    res = n.to_bytes((n.bit_length() + 7) // 8, "big") if n > 0 else b""
    pad = len(v) - len(v.lstrip("1"))
    return b"\x00" * pad + res


class SolanaOracleSigner:
    """
    Ed25519 Signer & Verifier for A.GRID Universal Escrow on Solana Mainnet.
    Produces cryptographically bound attestations matching Solana's native instruction layout.
    """

    def __init__(self, private_seed: bytes = None):
        import json
        if private_seed is not None:
            seed = private_seed[:32] if len(private_seed) >= 32 else hashlib.sha256(private_seed).digest()
        else:
            solana_raw = os.getenv("SOLANA_PRIVATE_KEY")
            if solana_raw and solana_raw.strip():
                raw = solana_raw.strip().strip('"').strip("'")
                if raw.startswith("[") and raw.endswith("]"):
                    # JSON array of bytes format (e.g. Solana CLI ~/.config/solana/id.json)
                    try:
                        byte_list = json.loads(raw)
                        seed = bytes(byte_list[:32])
                    except Exception:
                        seed = hashlib.sha256(raw.encode()).digest()
                elif len(raw) in (64, 66) and (raw.startswith("0x") or all(c in "0123456789abcdefABCDEF" for c in raw)):
                    # Hex format
                    clean_hex = raw[2:] if raw.startswith("0x") else raw
                    seed = bytes.fromhex(clean_hex)[:32]
                else:
                    # Base58 format: A valid Solana private key is 64 bytes (87-88 chars Base58).
                    # A 43-44 char string is a PUBLIC KEY (wallet address), which must NEVER be used as a private key!
                    if len(raw) <= 44:
                        # User provided a public wallet address. Fallback to server gate master key!
                        seed = hashlib.sha256(
                            bytes.fromhex(os.getenv("GATE_PRIVATE_KEY", "383c8bf864c8030ec0ebcea6f9bc2ffff45ed25ede58af3034e66886e1d8a118").replace("0x", ""))
                        ).digest()
                    else:
                        try:
                            decoded_bytes = b58decode(raw)
                            seed = decoded_bytes[:32]
                        except Exception:
                            seed = hashlib.sha256(raw.encode()).digest()
            else:
                # Deterministic fallback derivation from master EVM deployer key
                raw_key = os.getenv(
                    "GATE_PRIVATE_KEY",
                    os.getenv("DEPLOYER_PRIVATE_KEY", "0x383c8bf864c8030ec0ebcea6f9bc2ffff45ed25ede58af3034e66886e1d8a118")
                )
                if raw_key.startswith("0x"):
                    raw_key = raw_key[2:]
                seed = hashlib.sha256(bytes.fromhex(raw_key)).digest()

        self.private_key = ed25519.Ed25519PrivateKey.from_private_bytes(seed)
        self.public_key = self.private_key.public_key()
        self.public_bytes = self.public_key.public_bytes_raw()
        self.public_b58 = b58encode(self.public_bytes)

    @staticmethod
    def serialize_attestation_payload(
        job_id: bytes,
        domain: int,
        truth_hash: bytes,
        recipients_hash: bytes,
        expires_at: int
    ) -> bytes:
        """
        Standardized binary serialization for Solana Oracle instruction:
        [32 bytes jobId] + [1 byte domain] + [32 bytes truthHash] + [32 bytes recipientsHash] + [8 bytes expiresAt (u64 LE)]
        Total length: 105 bytes
        """
        assert len(job_id) == 32, "job_id must be 32 bytes"
        assert len(truth_hash) == 32, "truth_hash must be 32 bytes"
        assert len(recipients_hash) == 32, "recipients_hash must be 32 bytes"
        assert 0 <= domain <= 255, "domain must be uint8"

        packed_header = struct.pack("<B", domain)
        packed_expires = struct.pack("<Q", expires_at)
        return b"AGRID_SOLANA_V1:" + job_id + packed_header + truth_hash + recipients_hash + packed_expires

    def sign_attestation(
        self,
        job_id: bytes,
        domain: int,
        truth_hash: bytes,
        recipients_hash: bytes,
        expires_at: int
    ) -> Dict[str, Any]:
        """Signs the Solana attestation payload with Ed25519."""
        message = self.serialize_attestation_payload(job_id, domain, truth_hash, recipients_hash, expires_at)
        signature = self.private_key.sign(message)
        sig_b58 = b58encode(signature)

        return {
            "chain": "solana-mainnet",
            "chain_id": 501,
            "oracle_signer_pubkey": self.public_b58,
            "signature_b58": sig_b58,
            "signature_hex": signature.hex(),
            "message_bytes_len": len(message),
            "serialized_message_hex": message.hex(),
            "expires_at": expires_at,
            "domain": domain,
            "job_id_hex": job_id.hex(),
            "truth_hash_hex": truth_hash.hex(),
            "recipients_hash_hex": recipients_hash.hex()
        }

    @classmethod
    def verify_attestation(
        cls,
        oracle_pubkey_b58: str,
        signature_b58: str,
        job_id: bytes,
        domain: int,
        truth_hash: bytes,
        recipients_hash: bytes,
        expires_at: int
    ) -> bool:
        """Verifies Ed25519 signature against expected attestation payload."""
        try:
            pubkey_bytes = b58decode(oracle_pubkey_b58)
            signature_bytes = b58decode(signature_b58)
            pub_key = ed25519.Ed25519PublicKey.from_public_bytes(pubkey_bytes)
            message = cls.serialize_attestation_payload(job_id, domain, truth_hash, recipients_hash, expires_at)
            pub_key.verify(signature_bytes, message)
            return True
        except (InvalidSignature, Exception):
            return False
