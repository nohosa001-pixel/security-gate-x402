"""State Channel Merkle Accumulator for security-gate-x402 Micro-Batching.

Enables zero-latency off-chain $0.002 micro-payment aggregation.
Constructs binary cryptographic Merkle Trees to compress 500-1,000 off-chain fee calls
into a single L2 on-chain anchor settlement transaction, reducing sequencer gas costs by 99.8%.
"""

from __future__ import annotations

import hashlib
import time
from typing import Any, Dict, List, Optional, Tuple


class MicroPaymentTicket:
    """Represents an individual $0.002 verification fee deduction."""

    def __init__(
        self,
        ticket_id: int,
        agent_address: str,
        fee_usdc_units: int,  # 2000 units = $0.002 USDC (6 decimals)
        nonce: int,
        timestamp: Optional[int] = None,
    ):
        self.ticket_id = ticket_id
        self.agent_address = agent_address.lower()
        self.fee_usdc_units = fee_usdc_units
        self.nonce = nonce
        self.timestamp = timestamp or int(time.time())
        self.leaf_hash = self._compute_leaf_hash()

    def _compute_leaf_hash(self) -> bytes:
        """Deterministic leaf hashing: keccak/sha256(agent:ticket_id:fee:nonce:timestamp)."""
        leaf_preimage = (
            f"{self.agent_address}:{self.ticket_id}:{self.fee_usdc_units}:{self.nonce}:{self.timestamp}"
        ).encode("utf-8")
        return hashlib.sha256(leaf_preimage).digest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticket_id": self.ticket_id,
            "agent_address": self.agent_address,
            "fee_usdc_units": self.fee_usdc_units,
            "nonce": self.nonce,
            "timestamp": self.timestamp,
            "leaf_hash": "0x" + self.leaf_hash.hex(),
        }


class MerkleBatchAccumulator:
    """Aggregates off-chain micro-payments and computes batch Merkle roots."""

    def __init__(self, batch_limit: int = 500):
        self.batch_limit = batch_limit
        self.tickets: List[MicroPaymentTicket] = []
        self._ticket_counter = 0

    def add_ticket(self, agent_address: str, fee_usdc_units: int = 2000, nonce: int = 0) -> MicroPaymentTicket:
        """Append a new micro-payment ticket to the current batch."""
        self._ticket_counter += 1
        ticket = MicroPaymentTicket(
            ticket_id=self._ticket_counter,
            agent_address=agent_address,
            fee_usdc_units=fee_usdc_units,
            nonce=nonce,
        )
        self.tickets.append(ticket)
        return ticket

    @property
    def total_collected_units(self) -> int:
        return sum(t.fee_usdc_units for t in self.tickets)

    @property
    def count(self) -> int:
        return len(self.tickets)

    def is_batch_ready(self) -> bool:
        return len(self.tickets) >= self.batch_limit

    def compute_merkle_root(self) -> bytes:
        """Computes root hash of the binary Merkle Tree for the current batch."""
        if not self.tickets:
            return b"\x00" * 32

        leaves = [t.leaf_hash for t in self.tickets]
        current_level = leaves[:]

        while len(current_level) > 1:
            next_level = []
            for i in range(0, len(current_level), 2):
                left = current_level[i]
                # If odd number of nodes, duplicate the last node
                right = current_level[i + 1] if i + 1 < len(current_level) else left
                combined = left + right if left <= right else right + left
                parent = hashlib.sha256(combined).digest()
                next_level.append(parent)
            current_level = next_level

        return current_level[0]

    def generate_proof(self, ticket_index: int) -> List[Dict[str, str]]:
        """Generates audit proof path for a specific ticket in the batch."""
        if ticket_index < 0 or ticket_index >= len(self.tickets):
            raise IndexError("Ticket index out of bounds.")

        leaves = [t.leaf_hash for t in self.tickets]
        proof: List[Dict[str, str]] = []
        current_index = ticket_index
        current_level = leaves[:]

        while len(current_level) > 1:
            next_level = []
            for i in range(0, len(current_level), 2):
                left = current_level[i]
                right = current_level[i + 1] if i + 1 < len(current_level) else left
                combined = left + right if left <= right else right + left
                parent = hashlib.sha256(combined).digest()
                next_level.append(parent)

                if i == current_index:
                    proof.append({"position": "right", "hash": "0x" + right.hex()})
                elif i + 1 == current_index:
                    proof.append({"position": "left", "hash": "0x" + left.hex()})

            current_index = current_index // 2
            current_level = next_level

        return proof

    @staticmethod
    def verify_proof(leaf_hash: bytes, proof: List[Dict[str, str]], root: bytes) -> bool:
        """Verifies whether a given leaf hash belongs to the Merkle root."""
        computed = leaf_hash
        for step in proof:
            sibling = bytes.fromhex(step["hash"].replace("0x", ""))
            if step["position"] == "left":
                combined = sibling + computed if sibling <= computed else computed + sibling
            else:
                combined = computed + sibling if computed <= sibling else sibling + computed
            computed = hashlib.sha256(combined).digest()

        return computed == root

    def flush_batch(self) -> Tuple[bytes, int, int]:
        """Finalizes current batch and returns (root_hash, total_units, count) for on-chain settlement."""
        root = self.compute_merkle_root()
        total_units = self.total_collected_units
        total_count = self.count
        self.tickets.clear()
        return root, total_units, total_count
