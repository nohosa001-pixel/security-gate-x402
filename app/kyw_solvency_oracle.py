"""
A.GRID Counterparty KYW (Know Your Wallet) & Multi-Chain Solvency Oracle.
Provides deterministic pre-settlement customs & verification checks right before funds move:
1. OFAC / Mixer / Policy Blocked Address Screening (EVM & Solana)
2. Live On-Chain USDC Balance & Gas Solvency (Base, Polygon, Arbitrum, Ethereum, Solana)
3. In-Process Agent Credit Rating (CRS) & Optional Pre-Sign Security Gate Audit
"""

from __future__ import annotations

import hashlib
import json
import os
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.credit_rating_engine import credit_engine
from app.security_engine import audit_payload
from app.x402_verifier import is_sanctioned_address

DEFAULT_SANCTIONED_EVM = {
    "0x8589427373d6d84e98730d7795d8f6f8731fda16",  # Tornado Cash 0.1 ETH
    "0x722122df12d4e14e13ac3b6895a86e84145b6967",  # Tornado Cash Router
    "0xd90e2f925da726b50c4ed8d0fb90ad053324f31b",  # Tornado Cash Proxy
    "0x910cbd523d972eb0a6f4cae4618ad62622b39dbf",  # Tornado Cash 10 ETH
    "0xa160cdab225685da1d56aa342ad8841c3b53f291",  # Tornado Cash 100 ETH
    "0xd4b88df4d29f5cedd6857912842cff3b20c8cfa3",  # Tornado Cash 100 DAI
    "0xfd8610d20aa15b7b2e3be39b396a1bc3516c7144",  # Tornado Cash 1000 DAI
}

DEFAULT_SANCTIONED_SOLANA = {
    "Tor1xzb2Zyy1cUxXmyJfR8aNXuW9HG8Aw2gzsWEBLR6",
}

EVM_CHAIN_CONFIG: Dict[int, Dict[str, Any]] = {
    8453: {
        "name": "Base",
        "rpc": "https://mainnet.base.org",
        "usdc": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        "min_gas": 0.0001,
    },
    137: {
        "name": "Polygon",
        "rpc": "https://polygon-bor-rpc.publicnode.com",
        "usdc": "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359",
        "min_gas": 0.01,
    },
    42161: {
        "name": "Arbitrum",
        "rpc": "https://arb1.arbitrum.io/rpc",
        "usdc": "0xaf88d065e77c8cC2239327C5EDb3A432268e5831",
        "min_gas": 0.0001,
    },
    1: {
        "name": "Ethereum",
        "rpc": "https://ethereum-rpc.publicnode.com",
        "usdc": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
        "min_gas": 0.001,
    },
}

SOLANA_USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"

_kyw_stats = {"total_verifications": 0, "approved": 0, "rejected": 0, "review_required": 0}


def _json_rpc_post(url: str, payload: Dict[str, Any], timeout_sec: float = 5.0) -> Dict[str, Any]:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "AGRID-KYW-Oracle/1.0"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
        return json.loads(resp.read().decode("utf-8"))


def check_sanctions_and_mixer(address: str, chain_id: int) -> Dict[str, Any]:
    """Screens an EVM or Solana counterparty wallet against OFAC, mixer, and policy blocklists."""
    clean_addr = address.strip()
    norm = clean_addr.lower() if clean_addr.startswith("0x") else clean_addr

    extra_blocked = {
        (item.strip().lower() if item.strip().startswith("0x") else item.strip())
        for item in os.getenv("BLOCKED_ADDRESSES", "").split(",")
        if item.strip()
    }

    risk_flags: List[str] = []
    is_mixer_or_ofac = (
        (norm.startswith("0x") and norm in DEFAULT_SANCTIONED_EVM)
        or (not norm.startswith("0x") and norm in DEFAULT_SANCTIONED_SOLANA)
        or bool(is_sanctioned_address(clean_addr))
    )
    if is_mixer_or_ofac:
        risk_flags.append("SANCTIONED_OR_MIXER_ADDRESS")
    if norm in extra_blocked:
        risk_flags.append("POLICY_BLOCKED_ADDRESS")

    return {
        "address": clean_addr,
        "chain_id": chain_id,
        "ofac_clean": len(risk_flags) == 0,
        "mixer_exposed": is_mixer_or_ofac,
        "risk_flags": risk_flags,
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
    }


def check_wallet_solvency(
    address: str,
    chain_id: int,
    required_amount_usdc: float,
    timeout_sec: float = 5.0,
) -> Dict[str, Any]:
    """Queries live on-chain native gas and canonical USDC balance across EVM & Solana."""
    clean_addr = address.strip()

    if chain_id == 501:
        rpc_url = os.getenv("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com")
        try:
            bal_res = _json_rpc_post(
                rpc_url,
                {"jsonrpc": "2.0", "id": 1, "method": "getBalance", "params": [clean_addr]},
                timeout_sec=timeout_sec,
            )
            tok_res = _json_rpc_post(
                rpc_url,
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "getTokenAccountsByOwner",
                    "params": [clean_addr, {"mint": SOLANA_USDC_MINT}, {"encoding": "jsonParsed"}],
                },
                timeout_sec=timeout_sec,
            )
            lamports = int((bal_res.get("result") or {}).get("value", 0))
            sol_balance = round(lamports / 1e9, 6)
            usdc_balance = 0.0
            for acc in (tok_res.get("result") or {}).get("value", []):
                ui_amt = (
                    acc.get("account", {})
                    .get("data", {})
                    .get("parsed", {})
                    .get("info", {})
                    .get("tokenAmount", {})
                    .get("uiAmount")
                )
                if isinstance(ui_amt, (int, float)):
                    usdc_balance += float(ui_amt)
            usdc_balance = round(usdc_balance, 6)
            return {
                "address": clean_addr,
                "chain_id": 501,
                "chain_name": "Solana",
                "required_amount_usdc": required_amount_usdc,
                "usdc_balance": usdc_balance,
                "native_gas_balance": sol_balance,
                "has_sufficient_usdc": usdc_balance >= required_amount_usdc,
                "has_gas_for_settlement": sol_balance >= 0.0005,
                "source": "LIVE_RPC",
            }
        except Exception as exc:
            return {
                "address": clean_addr,
                "chain_id": 501,
                "chain_name": "Solana",
                "required_amount_usdc": required_amount_usdc,
                "usdc_balance": 0.0,
                "native_gas_balance": 0.0,
                "has_sufficient_usdc": False,
                "has_gas_for_settlement": False,
                "source": "RPC_UNAVAILABLE",
                "error": str(exc)[:180],
            }

    cfg = EVM_CHAIN_CONFIG.get(chain_id)
    if not cfg:
        return {
            "address": clean_addr,
            "chain_id": chain_id,
            "chain_name": "Unknown",
            "required_amount_usdc": required_amount_usdc,
            "usdc_balance": 0.0,
            "native_gas_balance": 0.0,
            "has_sufficient_usdc": False,
            "has_gas_for_settlement": False,
            "source": "RPC_UNAVAILABLE",
            "error": f"Unsupported chain_id: {chain_id}",
        }

    rpc_url = os.getenv(f"RPC_URL_{chain_id}") or (
        os.getenv("POLYGON_RPC_URL") if chain_id == 137 else None
    ) or cfg["rpc"]

    try:
        addr_hex = clean_addr.lower().removeprefix("0x").zfill(64)
        call_data = f"0x70a08231{addr_hex}"

        nat_res = _json_rpc_post(
            rpc_url,
            {"jsonrpc": "2.0", "id": 1, "method": "eth_getBalance", "params": [clean_addr, "latest"]},
            timeout_sec=timeout_sec,
        )
        tok_res = _json_rpc_post(
            rpc_url,
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "eth_call",
                "params": [{"to": cfg["usdc"], "data": call_data}, "latest"],
            },
            timeout_sec=timeout_sec,
        )
        raw_native = int(nat_res.get("result") or "0x0", 16)
        raw_usdc = int(tok_res.get("result") or "0x0", 16)
        native_gas = round(raw_native / 1e18, 6)
        usdc_balance = round(raw_usdc / 1e6, 6)

        return {
            "address": clean_addr,
            "chain_id": chain_id,
            "chain_name": cfg["name"],
            "required_amount_usdc": required_amount_usdc,
            "usdc_balance": usdc_balance,
            "native_gas_balance": native_gas,
            "has_sufficient_usdc": usdc_balance >= required_amount_usdc,
            "has_gas_for_settlement": native_gas >= cfg["min_gas"],
            "source": "LIVE_RPC",
        }
    except Exception as exc:
        return {
            "address": clean_addr,
            "chain_id": chain_id,
            "chain_name": cfg["name"],
            "required_amount_usdc": required_amount_usdc,
            "usdc_balance": 0.0,
            "native_gas_balance": 0.0,
            "has_sufficient_usdc": False,
            "has_gas_for_settlement": False,
            "source": "RPC_UNAVAILABLE",
            "error": str(exc)[:180],
        }


def verify_counterparty_kyw(
    counterparty_address: str,
    chain_id: int = 8453,
    required_amount_usdc: float = 0.0,
    escrow_job_id: Optional[str] = None,
    payload_to_audit: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Unified Pre-Settlement Tollgate:
    Combines Counterparty KYW (OFAC/mixer), Multi-Chain USDC Solvency, CRS Credit Rating,
    and optional <3ms Pre-Sign Security Gate audit in a single deterministic verdict.
    """
    sanctions = check_sanctions_and_mixer(counterparty_address, chain_id)
    solvency = check_wallet_solvency(counterparty_address, chain_id, required_amount_usdc)

    try:
        crs = credit_engine.get_credit_rating(counterparty_address)
        credit_score = int(crs.get("fico_score", crs.get("credit_score", 680)))
        credit_grade = str(crs.get("grade", "B"))
    except Exception:
        credit_score = 680
        credit_grade = "B"

    security_gate_result: Optional[Dict[str, Any]] = None
    security_blocked = False
    if payload_to_audit:
        report = audit_payload(payload_to_audit)
        security_blocked = report.verdict == "BLOCKED"
        security_gate_result = {
            "verdict": report.verdict,
            "risk_score": report.risk_score,
            "threats_count": len(report.threats),
        }

    reasons: List[str] = []
    if not sanctions["ofac_clean"]:
        reasons.extend(sanctions["risk_flags"])
    if security_blocked:
        reasons.append("SECURITY_GATE_BLOCKED")
    if credit_grade == "F" or credit_score < 400:
        reasons.append(f"LOW_CREDIT_GRADE_{credit_grade}")
    if solvency["source"] == "RPC_UNAVAILABLE":
        reasons.append("SOLVENCY_RPC_UNAVAILABLE")
    elif not solvency["has_sufficient_usdc"]:
        reasons.append(f"INSUFFICIENT_USDC ({solvency['usdc_balance']} < {required_amount_usdc})")

    if (
        not sanctions["ofac_clean"]
        or security_blocked
        or credit_grade == "F"
        or credit_score < 400
    ):
        verdict = "REJECTED"
    elif solvency["source"] == "RPC_UNAVAILABLE":
        verdict = "REVIEW_REQUIRED"
    elif not solvency["has_sufficient_usdc"]:
        verdict = "REJECTED"
    else:
        verdict = "APPROVED"

    _kyw_stats["total_verifications"] += 1
    _kyw_stats[verdict.lower()] += 1

    verified_at_utc = datetime.now(timezone.utc).isoformat()
    canonical = json.dumps(
        {
            "counterparty_address": counterparty_address.strip(),
            "chain_id": chain_id,
            "required_amount_usdc": required_amount_usdc,
            "verdict": verdict,
            "ofac_clean": sanctions["ofac_clean"],
            "usdc_balance": solvency["usdc_balance"],
            "credit_score": credit_score,
            "security_blocked": security_blocked,
            "verified_at_utc": verified_at_utc,
        },
        sort_keys=True,
    )
    proof_hash = "0x" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    return {
        "protocol": "A.GRID-KYW-SOLVENCY/1.0",
        "verdict": verdict,
        "reasons": reasons,
        "counterparty_address": counterparty_address.strip(),
        "chain_id": chain_id,
        "required_amount_usdc": required_amount_usdc,
        "escrow_job_id": escrow_job_id,
        "sanctions": sanctions,
        "solvency": solvency,
        "reputation": {
            "credit_score": credit_score,
            "credit_grade": credit_grade,
        },
        "security_gate": security_gate_result,
        "proof_hash": proof_hash,
        "verified_at_utc": verified_at_utc,
    }


def get_kyw_stats() -> Dict[str, Any]:
    return {
        "status": "active",
        "protocol": "A.GRID-KYW-SOLVENCY/1.0",
        "supported_chains": [8453, 137, 42161, 1, 501],
        "price_per_check_usdc": "0.02",
        **_kyw_stats,
    }
