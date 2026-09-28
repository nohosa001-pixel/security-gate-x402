"""
On-Chain Safe Guard Automation Engine for Agent Security Gate x402.
Provides end-to-end automated guard attachment, pre-flight security auditing,
EIP-712 attestation synthesis, and autonomous on-chain transaction execution.
"""

import os
import time
import json
from typing import Dict, Any, Optional
from web3 import Web3
from eth_account import Account
from eth_abi import encode
import eth_utils

from app.security_engine import audit_payload
from app.onchain_signer import onchain_signer


# Standard Safe storage slot for Guard address (keccak256("guard_manager.guard.address"))
SAFE_GUARD_STORAGE_SLOT = "0x4a204f620c8c5ccdca3fd54d003b799ba82d82afd266163c202d2d86c244ddc0"

# Default Polygon RPC & Deployed Safe Guard Addresses
DEFAULT_RPC_URLS = {
    137: os.getenv("POLYGON_RPC_URL", "https://polygon-bor-rpc.publicnode.com"),
    8453: os.getenv("BASE_RPC_URL", "https://mainnet.base.org"),
    42161: os.getenv("ARBITRUM_RPC_URL", "https://arb1.arbitrum.io/rpc"),
    1: os.getenv("ETHEREUM_RPC_URL", "https://eth.llamarpc.com")
}

DEFAULT_DEPLOYED_GUARDS = {
    137: "0x5d7CbDb7347DEe5Af8b8B64A298f3B5553cd851e",  # Official Verified Polygon SafeSecurityGateGuard
    8453: "0x5d7CbDb7347DEe5Af8b8B64A298f3B5553cd851e",
    42161: "0x5d7CbDb7347DEe5Af8b8B64A298f3B5553cd851e"
}


class GuardAutomationEngine:
    """Automates on-chain Guard deployment, attachment, and guarded agent execution."""

    def __init__(self):
        self.default_chain_id = 137
        self.rpc_urls = DEFAULT_RPC_URLS

    def get_web3(self, chain_id: int = 137) -> Web3:
        rpc = self.rpc_urls.get(chain_id, self.rpc_urls[137])
        return Web3(Web3.HTTPProvider(rpc))

    def check_guard_status(self, safe_address: str, chain_id: int = 137) -> Dict[str, Any]:
        """
        Inspects on-chain storage to check if a Guard is active on the given Safe.
        """
        try:
            w3 = self.get_web3(chain_id)
            safe_checksum = Web3.to_checksum_address(safe_address)

            # 1. Read guard storage slot
            raw_slot = w3.eth.get_storage_at(safe_checksum, SAFE_GUARD_STORAGE_SLOT)
            raw_hex = raw_slot.hex()
            clean_hex = raw_hex[-40:] if len(raw_hex) >= 40 else "0" * 40
            guard_address = Web3.to_checksum_address("0x" + clean_hex)

            is_active = guard_address != "0x0000000000000000000000000000000000000000"
            known_guard = DEFAULT_DEPLOYED_GUARDS.get(chain_id, "")
            is_official = is_active and (guard_address.lower() == known_guard.lower())

            # 2. Read Safe nonce
            nonce = int.from_bytes(w3.eth.call({"to": safe_checksum, "data": bytes.fromhex("affed0e0")}), 'big')

            return {
                "safe_address": safe_checksum,
                "chain_id": chain_id,
                "guard_attached": is_active,
                "guard_address": guard_address if is_active else None,
                "is_official_sheriff_guard": is_official,
                "safe_nonce": nonce,
                "status": "GUARDED" if is_active else "UNGUARDED_VULNERABLE",
                "recommended_action": "NONE" if is_active else "ATTACH_GUARD_IMMEDIATELY"
            }
        except Exception as e:
            return {
                "safe_address": safe_address,
                "chain_id": chain_id,
                "error": str(e),
                "status": "QUERY_FAILED"
            }

    def attach_guard_to_safe(
        self,
        safe_address: str,
        owner_private_key: str,
        guard_address: Optional[str] = None,
        chain_id: int = 137
    ) -> Dict[str, Any]:
        """
        Automates attaching the SafeSecurityGateGuard to a Safe{Wallet}.
        Executes via Safe's execTransaction using the owner's signature.
        """
        try:
            w3 = self.get_web3(chain_id)
            safe_checksum = Web3.to_checksum_address(safe_address)
            owner_account = Account.from_key(owner_private_key)

            target_guard = guard_address or DEFAULT_DEPLOYED_GUARDS.get(chain_id, DEFAULT_DEPLOYED_GUARDS[137])
            guard_checksum = Web3.to_checksum_address(target_guard)

            # 1. Fetch current Safe nonce
            safe_nonce = int.from_bytes(w3.eth.call({"to": safe_checksum, "data": bytes.fromhex("affed0e0")}), 'big')

            # 2. Build setGuard(address) calldata: selector 0xe19a9dd9
            set_guard_calldata = bytes.fromhex("e19a9dd9") + encode(["address"], [guard_checksum])

            # 3. Compute SafeTxHash via getTransactionHash(to, value, data, operation, safeTxGas, baseGas, gasPrice, gasToken, refundReceiver, nonce)
            get_tx_hash_sel = bytes.fromhex("d8d11f78")
            args = encode(
                ["address", "uint256", "bytes", "uint8", "uint256", "uint256", "uint256", "address", "address", "uint256"],
                [
                    safe_checksum,
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
            safe_tx_hash = w3.eth.call({"to": safe_checksum, "data": get_tx_hash_sel + args})

            # 4. Sign SafeTxHash with Owner Private Key
            signed_hash = Account._sign_hash(safe_tx_hash, owner_account.key)
            sig_bytes = signed_hash.signature

            # 5. Build execTransaction calldata: selector 0x6a761202
            exec_selector = bytes.fromhex("6a761202")
            exec_args = encode(
                ["address", "uint256", "bytes", "uint8", "uint256", "uint256", "uint256", "address", "address", "bytes"],
                [
                    safe_checksum,
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

            # 6. Simulate via eth_call
            w3.eth.call({
                "from": owner_account.address,
                "to": safe_checksum,
                "data": exec_calldata
            })

            # 7. Broadcast transaction
            gas_price = int(w3.eth.gas_price * 1.35)
            deployer_nonce = w3.eth.get_transaction_count(owner_account.address, "pending")
            tx_payload = {
                "from": owner_account.address,
                "to": safe_checksum,
                "data": exec_calldata,
                "nonce": deployer_nonce,
                "gasPrice": gas_price,
                "chainId": chain_id
            }
            gas_limit = w3.eth.estimate_gas(tx_payload)
            tx_payload["gas"] = int(gas_limit * 1.3)

            signed_tx = owner_account.sign_transaction(tx_payload)
            tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)

            receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

            return {
                "status": "GUARD_ATTACHED_SUCCESSFULLY" if receipt.status == 1 else "TRANSACTION_REVERTED",
                "safe_address": safe_checksum,
                "guard_address": guard_checksum,
                "tx_hash": tx_hash.hex(),
                "block_number": receipt.blockNumber,
                "gas_used": receipt.gasUsed,
                "receipt_status": receipt.status
            }
        except Exception as e:
            return {
                "status": "ATTACHMENT_FAILED",
                "safe_address": safe_address,
                "error": str(e)
            }

    def execute_guarded_transaction(
        self,
        safe_address: str,
        agent_private_key: str,
        to_address: str,
        value_wei: int,
        calldata: bytes,
        intent_description: str,
        chain_id: int = 137
    ) -> Dict[str, Any]:
        """
        Complete Autonomous Pipeline:
        1. Pre-flight security audit (<5ms AST, prompt injection, intent match).
        2. Revert if threat detected (0 gas loss to Safe).
        3. EIP-712 Proof-of-Safety Attestation generation by Security Gate Oracle.
        4. Package attestation with transaction and execute via Safe.
        """
        start_time = time.perf_counter()

        # Step 1: Pre-Flight Deterministic Audit
        audit = audit_payload(
            text=f"Intent: {intent_description} | Target: {to_address} | Value: {value_wei} | Calldata: {calldata.hex()}",
            is_code=False,
            ground_truth=intent_description
        )

        if not audit.is_safe or audit.risk_score > 30:
            return {
                "status": "BLOCKED_BY_SECURITY_GATE",
                "reason": "Excessive risk score or detected threat pattern in agent intent",
                "risk_score": audit.risk_score,
                "verdict": audit.verdict,
                "threats": audit.threats,
                "onchain_tx_sent": False,
                "gas_saved_wei": 150000 * 30000000000,
                "latency_ms": round((time.perf_counter() - start_time) * 1000, 2)
            }

        # Step 2: Generate Oracle EIP-712 Signature
        payload_repr = f"{to_address}:{value_wei}:{calldata.hex()}"
        attestation = onchain_signer.generate_eip712_signature(
            action_payload=payload_repr,
            risk_score=float(audit.risk_score / 100.0),
            verdict=audit.verdict,
            chain_id=chain_id,
            validity_seconds=300
        )

        # Step 3: Embed Oracle Attestation Proof into Calldata or Signature Hook
        # SafeSecurityGateGuard checks that transaction payload carried valid proof
        w3 = self.get_web3(chain_id)
        safe_checksum = Web3.to_checksum_address(safe_address)
        agent_account = Account.from_key(agent_private_key)

        safe_nonce = int.from_bytes(w3.eth.call({"to": safe_checksum, "data": bytes.fromhex("affed0e0")}), 'big')

        # Combine payload with attestation proof bytes (v, r, s, expiresAt, riskScore)
        proof_bytes = (
            bytes.fromhex(attestation["v"][2:].zfill(2)) +
            bytes.fromhex(attestation["r"][2:].zfill(64)) +
            bytes.fromhex(attestation["s"][2:].zfill(64)) +
            int(attestation["expires_at"]).to_bytes(8, 'big') +
            int(attestation["risk_score"]).to_bytes(1, 'big')
        )
        guarded_calldata = calldata + proof_bytes

        # Compute SafeTxHash
        get_tx_hash_sel = bytes.fromhex("d8d11f78")
        args = encode(
            ["address", "uint256", "bytes", "uint8", "uint256", "uint256", "uint256", "address", "address", "uint256"],
            [
                Web3.to_checksum_address(to_address),
                value_wei,
                guarded_calldata,
                0,
                0,
                0,
                0,
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000",
                safe_nonce
            ]
        )
        safe_tx_hash = w3.eth.call({"to": safe_checksum, "data": get_tx_hash_sel + args})

        # Agent signs SafeTxHash
        signed_hash = Account._sign_hash(safe_tx_hash, agent_account.key)
        agent_sig_bytes = signed_hash.signature

        # Build execTransaction
        exec_selector = bytes.fromhex("6a761202")
        exec_args = encode(
            ["address", "uint256", "bytes", "uint8", "uint256", "uint256", "uint256", "address", "address", "bytes"],
            [
                Web3.to_checksum_address(to_address),
                value_wei,
                guarded_calldata,
                0,
                0,
                0,
                0,
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000",
                agent_sig_bytes
            ]
        )
        exec_calldata = exec_selector + exec_args

        # Step 4: Simulate on-chain execution with eth_call
        try:
            w3.eth.call({
                "from": agent_account.address,
                "to": safe_checksum,
                "data": exec_calldata
            })
            sim_ok = True
        except Exception as sim_err:
            return {
                "status": "SIMULATION_REVERTED_BY_GUARD",
                "reason": f"Safe Guard rejected transaction: {str(sim_err)}",
                "risk_score": audit.risk_score,
                "onchain_tx_sent": False,
                "latency_ms": round((time.perf_counter() - start_time) * 1000, 2)
            }

        # Step 5: Broadcast transaction
        gas_price = int(w3.eth.gas_price * 1.35)
        agent_nonce = w3.eth.get_transaction_count(agent_account.address, "pending")
        tx_payload = {
            "from": agent_account.address,
            "to": safe_checksum,
            "data": exec_calldata,
            "nonce": agent_nonce,
            "gasPrice": gas_price,
            "chainId": chain_id
        }
        gas_limit = w3.eth.estimate_gas(tx_payload)
        tx_payload["gas"] = int(gas_limit * 1.3)

        signed_tx = agent_account.sign_transaction(tx_payload)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)

        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

        elapsed = round((time.perf_counter() - start_time) * 1000, 2)
        return {
            "status": "GUARDED_TRANSACTION_EXECUTED",
            "safe_address": safe_checksum,
            "target": to_address,
            "value_wei": value_wei,
            "tx_hash": tx_hash.hex(),
            "block_number": receipt.blockNumber,
            "gas_used": receipt.gasUsed,
            "risk_score": audit.risk_score,
            "verdict": audit.verdict,
            "eip712_attestation": {
                "signer": attestation["signer"],
                "expires_at": attestation["expires_at"],
                "v": attestation["v"],
                "r": attestation["r"],
                "s": attestation["s"]
            },
            "latency_ms": elapsed
        }


# Singleton engine instance
guard_automator = GuardAutomationEngine()
