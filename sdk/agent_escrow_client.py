"""
Agent Security Gate x402 - AgentEscrow Client SDK.
==================================================
Python Client for Autonomous Agent-to-Agent (M2M) Task Escrow,
Collateral Staking, and Proof-of-Safety Settlement.

Supported Chains:
- Polygon Mainnet (137):  0x5cC5Afa2a97599d492A3E408Fdd95fD0b520f173
- Base Mainnet (8453):     0x306e69E59E5bCEa769C6CeA76A79AFA8f2A5F408
- Arbitrum One (42161):    0x306e69E59E5bCEa769C6CeA76A79AFA8f2A5F408
"""

import os
import time
import json
import logging
from typing import Dict, Any, Optional, Tuple
import httpx
from eth_account import Account
import eth_utils

logger = logging.getLogger("AgentEscrowClient")

DEPLOYED_ESCROW_CONTRACTS = {
    137: "0x8ACafCEce0B1BFE140e75614b90FD1307b6f389d",    # Polygon
    8453: "0x99FEd65Cf2D5378182c3481B300124BB1a8Ad278",   # Base
    42161: "0x99FEd65Cf2D5378182c3481B300124BB1a8Ad278",  # Arbitrum One
}

DEFAULT_ORACLE_URL = os.environ.get(
    "SECURITY_GATE_ORACLE_URL",
    "https://agent-security-gate-x402-212942243360.asia-northeast3.run.app"
)

# Standard Minimal ABI for AgentEscrow.sol
AGENT_ESCROW_ABI = [
    {
        "inputs": [
            {"internalType": "address", "name": "worker", "type": "address"},
            {"internalType": "uint256", "name": "payoutAmount", "type": "uint256"},
            {"internalType": "uint256", "name": "requiredStake", "type": "uint256"},
            {"internalType": "bytes32", "name": "specHash", "type": "bytes32"},
            {"internalType": "uint256", "name": "durationSeconds", "type": "uint256"}
        ],
        "name": "createJob",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "uint256", "name": "jobId", "type": "uint256"}],
        "name": "depositStake",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "jobId", "type": "uint256"},
            {
                "components": [
                    {"internalType": "uint256", "name": "jobId", "type": "uint256"},
                    {"internalType": "bytes32", "name": "deliverableHash", "type": "bytes32"},
                    {"internalType": "uint8", "name": "riskScore", "type": "uint8"},
                    {"internalType": "string", "name": "verdict", "type": "string"},
                    {"internalType": "uint256", "name": "expiresAt", "type": "uint256"},
                    {"internalType": "uint8", "name": "v", "type": "uint8"},
                    {"internalType": "bytes32", "name": "r", "type": "bytes32"},
                    {"internalType": "bytes32", "name": "s", "type": "bytes32"}
                ],
                "internalType": "struct AgentEscrow.EscrowAttestation",
                "name": "proof",
                "type": "tuple"
            }
        ],
        "name": "completeJob",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "jobId", "type": "uint256"},
            {
                "components": [
                    {"internalType": "uint256", "name": "jobId", "type": "uint256"},
                    {"internalType": "bytes32", "name": "deliverableHash", "type": "bytes32"},
                    {"internalType": "uint8", "name": "riskScore", "type": "uint8"},
                    {"internalType": "string", "name": "verdict", "type": "string"},
                    {"internalType": "uint256", "name": "expiresAt", "type": "uint256"},
                    {"internalType": "uint8", "name": "v", "type": "uint8"},
                    {"internalType": "bytes32", "name": "r", "type": "bytes32"},
                    {"internalType": "bytes32", "name": "s", "type": "bytes32"}
                ],
                "internalType": "struct AgentEscrow.EscrowAttestation",
                "name": "proof",
                "type": "tuple"
            }
        ],
        "name": "slashJob",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "name": "jobs",
        "outputs": [
            {"internalType": "uint256", "name": "jobId", "type": "uint256"},
            {"internalType": "address", "name": "client", "type": "address"},
            {"internalType": "address", "name": "worker", "type": "address"},
            {"internalType": "uint256", "name": "payoutAmount", "type": "uint256"},
            {"internalType": "uint256", "name": "stakeAmount", "type": "uint256"},
            {"internalType": "bytes32", "name": "specHash", "type": "bytes32"},
            {"internalType": "uint8", "name": "status", "type": "uint8"},
            {"internalType": "uint256", "name": "createdAt", "type": "uint256"},
            {"internalType": "uint256", "name": "deadline", "type": "uint256"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "oracleSigner",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    }
]


class AgentEscrowClient:
    """
    Headless SDK Client for Autonomous AI Agents to interact with AgentEscrow.sol.
    """

    def __init__(
        self,
        private_key: Optional[str] = None,
        chain_id: int = 137,
        rpc_url: Optional[str] = None,
        contract_address: Optional[str] = None,
        oracle_url: str = DEFAULT_ORACLE_URL
    ):
        self.chain_id = chain_id
        self.oracle_url = oracle_url.rstrip("/")
        self.contract_address = contract_address or DEPLOYED_ESCROW_CONTRACTS.get(chain_id)
        
        self.private_key = private_key or os.environ.get("AGENT_PRIVATE_KEY")
        if self.private_key:
            self.account = Account.from_key(self.private_key)
            self.address = self.account.address
        else:
            self.account = None
            self.address = "0x0000000000000000000000000000000000000000"

        self.rpc_url = rpc_url
        self._w3 = None
        if self.rpc_url:
            try:
                from web3 import Web3
                self._w3 = Web3(Web3.HTTPProvider(self.rpc_url))
            except ImportError:
                pass

    @staticmethod
    def hash_spec(spec_text: str) -> str:
        """Computes Keccak-256 hash of task specification."""
        return "0x" + eth_utils.keccak(text=spec_text).hex()

    def request_attestation(
        self,
        job_id: int,
        deliverable: str,
        ground_truth_spec: Optional[str] = None,
        is_code: bool = True
    ) -> Dict[str, Any]:
        """
        Submits deliverable to Security Gate Cloud Run Oracle for deterministic audit
        and receives an EIP-712 signed EscrowAttestation.
        """
        payload = {
            "job_id": job_id,
            "deliverable": deliverable,
            "ground_truth_spec": ground_truth_spec,
            "is_code": is_code,
            "chain_id": self.chain_id,
            "verifying_contract": self.contract_address
        }

        # Try Cloud Run Oracle API first; if unavailable, fallback to local escrow engine
        endpoint = f"{self.oracle_url}/api/v1/escrow/audit" if not self.oracle_url.endswith("/api/v1") else f"{self.oracle_url}/escrow/audit"
        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.post(endpoint, json=payload)
                if resp.status_code == 200:
                    return resp.json()
        except Exception as e:
            logger.warning(f"Cloud Run Oracle offline ({e}), evaluating via local escrow_engine...")

        # Local deterministic fallback
        try:
            from app.escrow_engine import escrow_engine
            return escrow_engine.evaluate_deliverable(
                job_id=job_id,
                deliverable=deliverable,
                ground_truth_spec=ground_truth_spec,
                is_code=is_code,
                chain_id=self.chain_id,
                verifying_contract=self.contract_address or DEPLOYED_ESCROW_CONTRACTS.get(self.chain_id, "0x8ACafCEce0B1BFE140e75614b90FD1307b6f389d")
            )
        except Exception as err:
            raise RuntimeError(f"Failed to obtain oracle attestation: {err}")

    def create_job_calldata(
        self,
        worker: str,
        payout_usdc: float,
        stake_usdc: float,
        spec_text: str,
        duration_seconds: int = 86400
    ) -> Dict[str, Any]:
        """
        Generates transaction calldata for createJob.
        """
        payout_wei = int(payout_usdc * 1e6)
        stake_wei = int(stake_usdc * 1e6)
        spec_hash_bytes = eth_utils.keccak(text=spec_text)

        return {
            "to": self.contract_address,
            "worker": worker,
            "payout_wei": payout_wei,
            "stake_wei": stake_wei,
            "spec_hash": "0x" + spec_hash_bytes.hex(),
            "duration": duration_seconds
        }

    def format_attestation_tuple(self, attestation: Dict[str, Any]) -> tuple:
        """
        Converts attestation dict to Solidity tuple format for completeJob / slashJob.
        Supports both snake_case and camelCase field naming.
        """
        job_id = int(attestation.get("job_id") or attestation.get("jobId", 0))
        deliv_hash = str(attestation.get("deliverable_hash") or attestation.get("deliverableHash", "0x" + "0"*64))
        risk_score = int(attestation.get("risk_score") or attestation.get("riskScore", 0))
        verdict = str(attestation.get("verdict", "PASSED"))
        expires_at = int(attestation.get("expires_at") or attestation.get("expiresAt", 0))
        v = int(attestation.get("v", 27))
        r = str(attestation.get("r", "0x" + "0"*64))
        s = str(attestation.get("s", "0x" + "0"*64))

        return (
            job_id,
            bytes.fromhex(deliv_hash.replace("0x", "")),
            risk_score,
            verdict,
            expires_at,
            v,
            bytes.fromhex(r.replace("0x", "")),
            bytes.fromhex(s.replace("0x", ""))
        )
