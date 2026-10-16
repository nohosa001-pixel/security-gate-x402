"""
Automated Forensic Adjuster & EIP-712 Exploit Claim Verifier
============================================================
Off-chain forensic worker inspecting Base/Polygon/Arbitrum transaction receipts
and ERC-20 Transfer event logs to quantify genuine agent wallet loss and issue
EIP-712 ExploitClaimVerdict attestations for AgenticShieldPool.sol.
"""

import os
import time
from typing import Dict, Any, Optional
from eth_account import Account
from eth_account.messages import encode_typed_data
from web3 import Web3

# Base Mainnet configuration defaults (multichain configurable)
CHAIN_ID = int(os.environ.get("SHIELD_CHAIN_ID", "8453"))
DEFAULT_SHIELD_POOL = os.environ.get(
    "SHIELD_POOL_ADDRESS", "0x90308AedEe6430D11e5214cf9d2F563333D33Ef2"
)
SHIELD_POOL_ADDRESS = Web3.to_checksum_address(DEFAULT_SHIELD_POOL)

# USDC address on Base Mainnet (Native USDC 6 decimals)
DEFAULT_USDC_ADDRESS = os.environ.get(
    "SHIELD_USDC_ADDRESS", "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
)
USDC_ADDRESS = Web3.to_checksum_address(DEFAULT_USDC_ADDRESS)
ERC20_TRANSFER_TOPIC = Web3.keccak(text="Transfer(address,address,uint256)").hex()

# Default forensic adjuster private key for testing/dev
DEFAULT_FORENSIC_KEY = "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d"
FORENSIC_SIGNER_KEY = os.environ.get("FORENSIC_SIGNER_KEY", DEFAULT_FORENSIC_KEY)

SHIELD_EIP712_DOMAIN = {
    "name": "AGridAgenticShield",
    "version": "1",
    "chainId": CHAIN_ID,
    "verifyingContract": SHIELD_POOL_ADDRESS,
}

EXPLOIT_VERDICT_TYPES = {
    "ExploitClaimVerdict": [
        {"name": "claimId", "type": "bytes32"},
        {"name": "agentSafe", "type": "address"},
        {"name": "exploitedTxHash", "type": "bytes32"},
        {"name": "attestationNonce", "type": "bytes32"},
        {"name": "verifiedLossUsdc", "type": "uint256"},
        {"name": "category", "type": "uint8"},
        {"name": "incidentTimestamp", "type": "uint64"},
        {"name": "verdictExpiry", "type": "uint64"},
    ]
}


class AutomatedForensicAdjuster:
    """
    Automated Loss Investigator & Claim Adjuster for Autonomous Agents.
    Audits on-chain transaction traces and signs EIP-712 ExploitClaimVerdict proofs.
    """

    def __init__(
        self,
        rpc_url: Optional[str] = None,
        forensic_private_key: str = FORENSIC_SIGNER_KEY,
        chain_id: int = CHAIN_ID,
        verifying_pool_address: str = SHIELD_POOL_ADDRESS,
        usdc_address: str = USDC_ADDRESS
    ):
        self.w3 = Web3(Web3.HTTPProvider(rpc_url)) if rpc_url else None
        self.signer_key = forensic_private_key
        self.signer_address = Account.from_key(forensic_private_key).address
        self.chain_id = chain_id
        self.pool_address = Web3.to_checksum_address(verifying_pool_address)
        self.usdc_address = Web3.to_checksum_address(usdc_address)

    def verify_onchain_loss_and_sign_verdict(
        self,
        agent_safe: str,
        exploited_tx_hash: str,
        attestation_nonce: str,
        authorized_max_spend: int,
        exploit_category: int = 0,
        receipt: Optional[Dict[str, Any]] = None,
        claim_expiry_seconds: int = 3600
    ) -> Dict[str, Any]:
        """
        1) Audits transaction receipt for actual USDC outflow from agentSafe.
        2) Calculates verified net loss over the authorized SafetyAttestation limit.
        3) Issues an EIP-712 ExploitClaimVerdict signature for AgenticShieldPool.sol.
        """
        agent_checksum = Web3.to_checksum_address(agent_safe)

        # Retrieve receipt if not passed explicitly
        if receipt is None:
            if not self.w3:
                raise ValueError("Web3 RPC provider not configured and no receipt provided.")
            receipt = self.w3.eth.get_transaction_receipt(exploited_tx_hash)

        if not receipt or receipt.get("status") != 1:
            raise ValueError("Transaction did not execute or reverted (0 loss)")

        # ERC-20 USDC Transfer logs analysis
        actual_usdc_outflow = 0
        padded_agent = "0x" + agent_checksum[2:].lower().rjust(64, "0")

        for log in receipt.get("logs", []):
            log_addr = log.get("address", "")
            if isinstance(log_addr, bytes):
                log_addr = "0x" + log_addr.hex()
            if log_addr.lower() == self.usdc_address.lower():
                topics = [
                    t.hex() if isinstance(t, bytes) else str(t)
                    for t in log.get("topics", [])
                ]
                if len(topics) >= 3 and topics[0].lower() == ERC20_TRANSFER_TOPIC.lower():
                    # Check if 'from' address matches agent_safe
                    if topics[1].lower() == padded_agent:
                        data = log.get("data", "0x0")
                        if isinstance(data, bytes):
                            data_hex = data.hex()
                        elif isinstance(data, str):
                            data_hex = data.replace("0x", "")
                        else:
                            data_hex = hex(data)[2:]
                        amount = int(data_hex or "0", 16)
                        actual_usdc_outflow += amount

        # Loss determination logic:
        # Category 0 (AST_SANDBOX_BYPASS) or 3 (CORRUPTED_ORACLE_PAYLOAD):
        # Malicious code execution or corrupted oracle payload compromises the whole tx.
        verified_loss = max(0, actual_usdc_outflow - authorized_max_spend)
        if verified_loss == 0 and actual_usdc_outflow > 0:
            if exploit_category in (0, 1, 3):
                # Total outflow recognized as exploit loss
                verified_loss = actual_usdc_outflow

        if verified_loss == 0:
            raise ValueError("No verifiable USDC outflow detected in transaction logs")

        # Deterministic claim ID: keccak256(agentSafe || exploitedTxHash)
        clean_tx_hex = exploited_tx_hash.replace("0x", "").zfill(64)
        clean_nonce_hex = attestation_nonce.replace("0x", "").zfill(64)
        claim_id = Web3.keccak(
            hexstr=agent_checksum[2:] + clean_tx_hex
        )
        now = int(time.time())
        expiry = now + claim_expiry_seconds

        domain = {
            "name": "AGridAgenticShield",
            "version": "1",
            "chainId": self.chain_id,
            "verifyingContract": self.pool_address,
        }

        verdict_data = {
            "claimId": claim_id,
            "agentSafe": agent_checksum,
            "exploitedTxHash": bytes.fromhex(clean_tx_hex),
            "attestationNonce": bytes.fromhex(clean_nonce_hex),
            "verifiedLossUsdc": int(verified_loss),
            "category": int(exploit_category),
            "incidentTimestamp": now,
            "verdictExpiry": expiry,
        }

        signable = encode_typed_data(domain, EXPLOIT_VERDICT_TYPES, verdict_data)
        signed = Account.sign_message(signable, private_key=self.signer_key)

        return {
            "verdict": {
                "claimId": "0x" + claim_id.hex(),
                "agentSafe": agent_checksum,
                "exploitedTxHash": "0x" + clean_tx_hex,
                "attestationNonce": "0x" + clean_nonce_hex,
                "verifiedLossUsdc": verified_loss,
                "category": exploit_category,
                "incidentTimestamp": now,
                "verdictExpiry": expiry,
            },
            "forensicSignature": "0x" + signed.signature.hex(),
            "forensicSigner": self.signer_address,
            "auditSummary": {
                "actualUsdcOutflow": actual_usdc_outflow,
                "authorizedMaxSpend": authorized_max_spend,
                "verifiedLossUsdc": verified_loss,
                "poolAddress": self.pool_address
            }
        }


# Default singleton instance
forensic_adjuster = AutomatedForensicAdjuster()
