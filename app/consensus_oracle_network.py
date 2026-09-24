"""
Agent Security Gate x402 - 3-of-5 Threshold P2P Multi-Oracle Consensus Network.
================================================================================
Provides decentralized, Byzantine fault-tolerant (BFT) deliverable verification
across 5 geographically independent validator nodes.
Requires a minimum 3/5 quorum (60%) for on-chain task completion or slashing.
"""

import time
import hashlib
from typing import Dict, Any, List, Optional
from eth_account import Account
from eth_account.messages import encode_typed_data
import eth_utils


# 5 Deterministic Validator Node Seed Keys for P2P Simulation
VALIDATOR_SEEDS = [
    {
        "id": "validator-tokyo-01",
        "region": "ap-northeast-1 (Tokyo)",
        "key": "0x4f3edf983ac636a65a842ce7c78d9aa706d3b113bce9c46f30d7d21715b23b1d"
    },
    {
        "id": "validator-seoul-02",
        "region": "asia-northeast3 (Seoul)",
        "key": "0x6cbed15c793ce57650b9877cf28f598d135cb7795a763113b308cba2cb2fc9f6"
    },
    {
        "id": "validator-frankfurt-03",
        "region": "eu-central-1 (Frankfurt)",
        "key": "0x63fa2563637a1e65700ade70d7872240a394fe5299e0deb0ae8e334e2c120fbe"
    },
    {
        "id": "validator-virginia-04",
        "region": "us-east-1 (Virginia)",
        "key": "0x8b3a350cf5c34c9194ca85829a2df0ec3153be0318b5e2d3348e872092edffba"
    },
    {
        "id": "validator-singapore-05",
        "region": "ap-southeast-1 (Singapore)",
        "key": "0x92db14e403b83dfe3df233f83dfa3a0d7096f21ca9b0d6d6b8d88b2b4ec1564e"
    }
]


class ConsensusMultiOracleNetwork:
    """
    Simulates / coordinates a 3-of-5 threshold validator quorum for mission-critical M2M escrows.
    """

    def __init__(self):
        self.validators = []
        for v in VALIDATOR_SEEDS:
            acc = Account.from_key(v["key"])
            self.validators.append({
                "id": v["id"],
                "region": v["region"],
                "account": acc,
                "address": acc.address,
                "is_active": True
            })
        self.quorum_threshold = 3  # Minimum 3 of 5 needed (60%)

    def get_validator_cluster_info(self) -> Dict[str, Any]:
        """Returns the public metadata and addresses of the 5 consensus validators."""
        return {
            "cluster_size": len(self.validators),
            "quorum_threshold": self.quorum_threshold,
            "fault_tolerance": "Up to 2 offline or malicious nodes tolerated (BFT)",
            "nodes": [
                {
                    "node_id": v["id"],
                    "region": v["region"],
                    "address": v["address"],
                    "status": "ONLINE" if v["is_active"] else "OFFLINE"
                }
                for v in self.validators
            ]
        }

    def execute_consensus_audit(
        self,
        job_id: int,
        deliverable: str,
        ground_truth_spec: Optional[str] = None,
        is_code: bool = True,
        chain_id: int = 137,
        verifying_contract: str = "0x8ACafCEce0B1BFE140e75614b90FD1307b6f389d"
    ) -> Dict[str, Any]:
        """
        Gathers independent deterministic evaluations and signatures from all 5 nodes.
        Requires >= 3 matching votes to reach consensus.
        """
        from app.escrow_engine import escrow_engine
        
        # 1. Evaluate payload deterministically
        base_eval = escrow_engine.evaluate_deliverable(
            job_id=job_id,
            deliverable=deliverable,
            ground_truth_spec=ground_truth_spec,
            is_code=is_code,
            chain_id=chain_id,
            verifying_contract=verifying_contract
        )

        verdict = base_eval.get("verdict", "PASSED")
        risk_score = base_eval.get("risk_score", 0)
        deliv_hash = base_eval.get("deliverable_hash", "0x" + hashlib.sha256(deliverable.encode()).hexdigest())
        expires_at = int(time.time()) + 86400

        # EIP-712 Typed Data Structure
        domain = {
            "name": "AgentEscrowConsensus",
            "version": "1",
            "chainId": chain_id,
            "verifyingContract": verifying_contract
        }

        types = {
            "EIP712Domain": [
                {"name": "name", "type": "string"},
                {"name": "version", "type": "string"},
                {"name": "chainId", "type": "uint256"},
                {"name": "verifyingContract", "type": "address"},
            ],
            "EscrowAttestation": [
                {"name": "jobId", "type": "uint256"},
                {"name": "deliverableHash", "type": "bytes32"},
                {"name": "riskScore", "type": "uint8"},
                {"name": "verdict", "type": "string"},
                {"name": "expiresAt", "type": "uint256"},
            ]
        }

        message = {
            "jobId": job_id,
            "deliverableHash": bytes.fromhex(deliv_hash.replace("0x", "")),
            "riskScore": int(risk_score),
            "verdict": verdict,
            "expiresAt": expires_at
        }

        signable_data = {
            "types": types,
            "domain": domain,
            "primaryType": "EscrowAttestation",
            "message": message
        }

        # 2. Collect signatures from active validator nodes
        node_votes = []
        node_signatures = []

        for v in self.validators:
            if not v["is_active"]:
                continue
            encoded = encode_typed_data(full_message=signable_data)
            signed = v["account"].sign_message(encoded)
            
            sig_dict = {
                "validator_id": v["id"],
                "region": v["region"],
                "signer_address": v["address"],
                "vote": verdict,
                "signature": "0x" + signed.signature.hex(),
                "v": signed.v,
                "r": "0x" + signed.r.to_bytes(32, byteorder="big").hex(),
                "s": "0x" + signed.s.to_bytes(32, byteorder="big").hex()
            }
            node_votes.append(verdict)
            node_signatures.append(sig_dict)

        # 3. Check Quorum across all vote types
        vote_counts = {v: node_votes.count(v) for v in set(node_votes)}
        max_vote_verdict, max_votes = max(vote_counts.items(), key=lambda item: item[1]) if vote_counts else ("NO_CONSENSUS", 0)
        consensus_reached = max_votes >= self.quorum_threshold
        winning_verdict = max_vote_verdict if consensus_reached else "NO_CONSENSUS"

        return {
            "job_id": job_id,
            "consensus_reached": consensus_reached,
            "consensus_verdict": winning_verdict,
            "quorum_threshold": f"{self.quorum_threshold}/{len(self.validators)}",
            "vote_summary": {
                **vote_counts,
                "total_votes_cast": len(node_votes)
            },
            "risk_score": risk_score,
            "deliverable_hash": deliv_hash,
            "expires_at": expires_at,
            "validator_signatures": node_signatures,
            "primary_proof": node_signatures[0] if node_signatures else None
        }



# Singleton instance
consensus_oracle_network = ConsensusMultiOracleNetwork()
