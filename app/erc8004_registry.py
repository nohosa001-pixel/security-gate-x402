"""Polygon ERC-8004 (Trustless Agents) Identity, Reputation & Validation Integration.

Connects A.GRID's <5ms Security Gate, x402 Universal Escrow, and MCP/A2A endpoints
to Polygon's official ERC-8004 singleton registries (Mainnet & Amoy).
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Dict, List, Optional
import urllib.request

from eth_abi import decode as abi_decode
from eth_abi import encode as abi_encode
from eth_utils import keccak

from app.security_engine import audit_payload

DEFAULT_HUB_BASE_URL = "https://agent-security-gate-x402-212942243360.asia-northeast3.run.app"

ERC8004_DEPLOYMENTS: Dict[str, Dict[str, Any]] = {
    "polygon-mainnet": {
        "chain_id": 137,
        "rpc_url": "https://polygon-rpc.com",
        "IdentityRegistry": "0x8004A169FB4a3325136EB29fA0ceB6D2e539a432",
        "ReputationRegistry": "0x8004BAa17C55a88189AE136b182e5fdA19dE9b63",
        "ValidationRegistry": None,
    },
    "polygon-amoy": {
        "chain_id": 80002,
        "rpc_url": "https://rpc-amoy.polygon.technology",
        "IdentityRegistry": "0x8004ad19E14B9e0654f73353e8a0B600D46C2898",
        "ReputationRegistry": "0x8004B12F4C2B42d00c46479e859C92e39044C930",
        "ValidationRegistry": "0x8004C11C213ff7BaD36489bcBDF947ba5eee289B",
    },
}


def _fn_selector(signature: str) -> str:
    """Compute 4-byte Ethereum function selector hex prefix."""
    return "0x" + keccak(text=signature)[:4].hex()


def _eth_call(rpc_url: str, to: str, data: str, timeout_s: float = 5.0) -> str:
    """Perform deterministic read-only eth_call via JSON-RPC."""
    body = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "eth_call",
            "params": [{"to": to, "data": data}, "latest"],
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        rpc_url,
        data=body,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        parsed = json.loads(resp.read().decode("utf-8"))
    if "error" in parsed:
        raise RuntimeError(f"RPC eth_call error: {parsed['error']}")
    return str(parsed.get("result", "0x"))


def build_agrid_registration_json(
    base_url: str = DEFAULT_HUB_BASE_URL,
    agent_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Generate the canonical ERC-8004 agent registration JSON for A.GRID."""
    base = base_url.rstrip("/")
    registrations: List[Dict[str, Any]] = []
    if agent_id is not None:
        registrations.append(
            {
                "agentId": agent_id,
                "agentRegistry": f"eip155:137:{ERC8004_DEPLOYMENTS['polygon-mainnet']['IdentityRegistry']}",
            }
        )

    return {
        "type": "https://eips.ethereum.org/EIPS/eip-8004#registration-v1",
        "name": "A.GRID Security Gate & Universal Escrow",
        "description": (
            "Sub-5ms deterministic AST & prompt-injection firewall, x402 autonomous escrow "
            "clearinghouse, and RWA/DePIN truth oracle across Solana, Polygon, Base, and Arbitrum."
        ),
        "image": f"{base}/static/agrid-logo.png",
        "services": [
            {
                "name": "MCP",
                "endpoint": f"{base}/mcp/tools",
                "version": "2025-06-18",
            },
            {
                "name": "A2A",
                "endpoint": f"{base}/.well-known/agent-card.json",
                "version": "0.3.0",
            },
            {
                "name": "x402-Escrow-Audit",
                "endpoint": f"{base}/api/v1/escrow/audit",
                "version": "1.0",
            },
            {
                "name": "ERC8004-Validation-Oracle",
                "endpoint": f"{base}/api/v1/erc8004/validate",
                "version": "1.0",
            },
        ],
        "onchainSettlement": {
            "polygonOmsPolicy": "0x4A28F9A2E6D0DcB69791980560FC8364A514f205",
            "polygonEscrow": "0x8ACafCEce0B1BFE140e75614b90FD1307b6f389d",
            "solanaEscrowProgram": "AGR3W3R9pKxnuZGYrpaggfkbMKVrjoniLaGvi1voBFSC",
            "solanaSecurityGateProgram": "AGRAtNxF474xZFin5iZaxBKE2fKNKPih7qYPEm3mu9oN",
        },
        "x402Support": True,
        "active": True,
        "registrations": registrations,
        "supportedTrust": ["reputation", "crypto-economic", "tee-attestation"],
    }


def build_register_calldata(agent_uri: str, network: str = "polygon-mainnet") -> Dict[str, Any]:
    """Build unsigned calldata for IdentityRegistry.register(string agentURI)."""
    cfg = ERC8004_DEPLOYMENTS.get(network)
    if not cfg:
        raise ValueError(f"Unsupported ERC-8004 network: {network}")

    encoded_args = abi_encode(["string"], [agent_uri])
    calldata = _fn_selector("register(string)") + encoded_args.hex()
    return {
        "network": network,
        "chain_id": cfg["chain_id"],
        "to": cfg["IdentityRegistry"],
        "function": "register(string)",
        "agent_uri": agent_uri,
        "data": calldata,
        "value": "0x0",
    }


def build_reputation_feedback_payload(
    *,
    agent_id: int,
    score: int,
    x402_tx_hash: str,
    chain_id: int = 137,
    tag1: str = "x402-settlement",
    tag2: str = "security-gate-passed",
    feedback_uri_base: str = DEFAULT_HUB_BASE_URL,
) -> Dict[str, Any]:
    """Build an ERC-8004 ReputationRegistry off-chain feedback record linked to an x402 proof."""
    if not 0 <= score <= 100:
        raise ValueError("ERC-8004 feedback score must be between 0 and 100")
    if not x402_tx_hash.strip():
        raise ValueError("x402_tx_hash is required to anchor payment proof")

    record = {
        "schema": "erc8004-reputation-feedback-v1",
        "agentId": agent_id,
        "score": score,
        "tags": [tag1, tag2],
        "proofOfPayment": {
            "protocol": "x402",
            "chainId": chain_id,
            "txHash": x402_tx_hash,
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    canonical = json.dumps(record, sort_keys=True, separators=(",", ":")).encode("utf-8")
    feedback_hash = "0x" + hashlib.sha256(canonical).hexdigest()

    return {
        "agentId": agent_id,
        "value": score,
        "valueDecimals": 0,
        "tag1": tag1,
        "tag2": tag2,
        "feedbackURI": f"{feedback_uri_base.rstrip('/')}/api/v1/erc8004/feedback/{feedback_hash}",
        "feedbackHash": feedback_hash,
        "record": record,
    }


def build_validation_response_payload(
    *,
    payload_text: str,
    is_code: bool = False,
    ground_truth: Optional[str] = None,
    request_hash: Optional[str] = None,
    response_uri_base: str = DEFAULT_HUB_BASE_URL,
) -> Dict[str, Any]:
    """Run A.GRID's <5ms Security Gate and format as an ERC-8004 ValidationRegistry response."""
    audit = audit_payload(text=payload_text, is_code=is_code, ground_truth=ground_truth)
    computed_req_hash = request_hash or (
        "0x" + hashlib.sha256(payload_text.encode("utf-8")).hexdigest()
    )

    # ERC-8004 response score: 0-100 where 100 = completely safe/valid, 0 = blocked/failed
    if not audit.is_safe:
        validation_score = 0
        tag = "SECURITY_BLOCKED"
    else:
        validation_score = max(0, min(100, int(round((1.0 - audit.risk_score) * 100))))
        tag = "PASSED" if validation_score >= 70 else "REVIEW_REQUIRED"

    evidence = {
        "schema": "erc8004-validation-response-v1",
        "requestHash": computed_req_hash,
        "verdict": audit.verdict,
        "isSafe": audit.is_safe,
        "riskScore": audit.risk_score,
        "validationScore": validation_score,
        "threats": audit.threats,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    response_hash = "0x" + hashlib.sha256(
        json.dumps(evidence, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()

    return {
        "requestHash": computed_req_hash,
        "response": validation_score,
        "responseURI": f"{response_uri_base.rstrip('/')}/api/v1/erc8004/validations/{response_hash}",
        "responseHash": response_hash,
        "tag": tag,
        "audit": evidence,
    }


def query_identity_onchain(
    agent_id: int,
    network: str = "polygon-mainnet",
    rpc_url: Optional[str] = None,
) -> Dict[str, Any]:
    """Read-only lookup of an agentId on Polygon Mainnet or Amoy IdentityRegistry."""
    cfg = ERC8004_DEPLOYMENTS.get(network)
    if not cfg:
        raise ValueError(f"Unsupported ERC-8004 network: {network}")

    target_rpc = rpc_url or cfg["rpc_url"]
    registry = cfg["IdentityRegistry"]

    encoded_id = abi_encode(["uint256"], [agent_id]).hex()
    owner_raw = _eth_call(target_rpc, registry, _fn_selector("ownerOf(uint256)") + encoded_id)
    uri_raw = _eth_call(target_rpc, registry, _fn_selector("tokenURI(uint256)") + encoded_id)

    owner_addr = abi_decode(["address"], bytes.fromhex(owner_raw.removeprefix("0x")))[0]
    token_uri = abi_decode(["string"], bytes.fromhex(uri_raw.removeprefix("0x")))[0]

    return {
        "network": network,
        "chain_id": cfg["chain_id"],
        "registry": registry,
        "agent_id": agent_id,
        "owner": owner_addr,
        "token_uri": token_uri,
    }

