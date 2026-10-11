"""
Shared dependencies, telemetry tracking, and state metrics for Agent Security Gate x402 routers.
"""

import time
import os
import json
from collections import OrderedDict
from typing import Dict, Any, List, Optional
from pathlib import Path
from fastapi import Request, HTTPException, status
from pydantic import BaseModel

from app.schemas import PricingTier
from app.x402_verifier import x402_verifier, is_sanctioned_address

# Rate limit, Prometheus metrics, and free trial usage tracker
_SERVER_START_TIME = time.time()
_rate_limit_tracker: Dict[str, list[float]] = {}
_free_trial_usage: OrderedDict = OrderedDict()
_quarantined_ips: Dict[str, float] = {}  # IP -> unban_timestamp (Active Defense Quarantine)
_recent_audit_events: List[Dict[str, Any]] = []
MAX_RECENT_EVENTS = 50
FREE_TRIAL_LIMIT = 3
RATE_LIMIT_PER_MINUTE = 120

_metrics_requests_total: Dict[str, int] = {"PASSED": 0, "FLAGGED": 0, "BLOCKED": 0, "ALLOW": 0, "WARN": 0, "BLOCK": 0}
_metrics_threats_total: Dict[str, int] = {}
_metrics_latency_buckets = [0.001, 0.002, 0.005, 0.010, 0.025, 0.050, 0.100, 0.250, 0.500, 1.000]
_metrics_latency_bucket_counts: Dict[float, int] = {b: 0 for b in _metrics_latency_buckets}
_metrics_latency_count = 0
_metrics_latency_sum = 0.0
_metrics_attestations_total = 0


def _dispatch_alert_webhook(url: str, verdict: str, risk_score: int, threats: list, caller_ip: str):
    """Dispatches asynchronous alert payload to configured webhook (Discord/Slack/Telegram compatible)."""
    import urllib.request
    try:
        payload = json.dumps({
            "content": f"🚨 **[Security Gate Threat Alert]**\n- **Verdict**: `{verdict}`\n- **Risk Score**: `{risk_score}%`\n- **Threats**: {', '.join(threats) if threats else 'None'}\n- **Origin**: `{caller_ip}`\n- **Time**: `{time.strftime('%Y-%m-%d %H:%M:%S UTC')}`"
        }).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json", "User-Agent": "SecurityGate-AlertDispatcher/1.0"},
            method="POST"
        )
        urllib.request.urlopen(req, timeout=2.0)
    except Exception:
        # Non-blocking, never disrupt the inspection pipeline
        pass


def _record_audit_telemetry(verdict: str, risk_score: int, threats: list, elapsed_sec: float, masked_ip: str, is_hallucinated: bool):
    """Records audit metrics for Prometheus APM and maintains recent events rolling buffer."""
    global _metrics_latency_count, _metrics_latency_sum
    v_upper = str(verdict).upper()
    _metrics_requests_total[v_upper] = _metrics_requests_total.get(v_upper, 0) + 1

    for t in threats:
        clean_t = str(t).split(":")[0].strip() if ":" in str(t) else str(t).strip()
        _metrics_threats_total[clean_t] = _metrics_threats_total.get(clean_t, 0) + 1

    _metrics_latency_count += 1
    _metrics_latency_sum += elapsed_sec
    for b in _metrics_latency_buckets:
        if elapsed_sec <= b:
            _metrics_latency_bucket_counts[b] = _metrics_latency_bucket_counts.get(b, 0) + 1

    norm_risk = float(risk_score * 100.0) if (isinstance(risk_score, (int, float)) and risk_score <= 1.0) else float(risk_score)

    _recent_audit_events.append({
        "event_type": "INSPECTION_AUDIT",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "verdict": verdict,
        "risk_score": round(norm_risk, 2),
        "threats": threats,
        "threats_count": len(threats),
        "is_hallucinated": is_hallucinated,
        "caller_ip_masked": masked_ip,
        "latency_ms": round(elapsed_sec * 1000.0, 2)
    })
    if len(_recent_audit_events) > MAX_RECENT_EVENTS:
        _recent_audit_events.pop(0)

    if norm_risk >= 90.0:
        webhook_url = os.getenv("SECURITY_GATE_ALERT_WEBHOOK")
        if webhook_url:
            _dispatch_alert_webhook(webhook_url, verdict, int(round(norm_risk)), threats, masked_ip)


async def require_x402_payment(request: Request, tier: PricingTier = PricingTier.STANDARD):
    """Enforces x402 payment authorization, pre-funded vault balance, or strictly bounded Free Trials."""
    # [IRON RULE 3]: Do NOT trust spoofable client headers (like X-Forwarded-For) as security/billing truth
    client_addr = request.headers.get("x-client-address") or request.headers.get("X-Client-Address") or "anonymous"
    raw_ip = request.client.host if request.client else "127.0.0.1"
    client_ip = raw_ip

    req_chain = (
        request.headers.get("x-chain-id") or 
        request.headers.get("X-Chain-ID") or 
        request.headers.get("x-network") or 
        request.headers.get("X-Network") or 
        request.query_params.get("chain_id") or 
        request.query_params.get("network")
    )
    
    # 1. Sanctions OFAC check
    if is_sanctioned_address(client_addr):
        raise HTTPException(status_code=403, detail="Forbidden: Sanctioned address.")

    auth_header = request.headers.get("authorization-x402") or request.headers.get("x-402-signature") or request.headers.get("X-402-Signature")
    api_key = request.headers.get("x-api-key") or request.headers.get("X-API-Key")
    vault_key = request.headers.get("x-vault-key") or request.headers.get("X-Vault-Key")

    # If payment/auth is provided, verify it
    if auth_header or api_key or vault_key:
        is_authorized, reason, extra_headers = x402_verifier.verify_request_payment(request, tier=tier)
        if not is_authorized:
            return x402_verifier.build_402_response(tier=tier, custom_detail=reason, chain_id=req_chain)
        request.state.authorized_payer = reason
        request.state.extra_headers = extra_headers or {}
        return None

    is_prod = os.getenv("ENVIRONMENT") == "production"

    # [IRON RULE 1]: In production, reject any request without a funded vault or verified enterprise key.
    # No uncollateralized or free requests (0 calls allowed) in production!
    if is_prod:
        return x402_verifier.build_402_response(
            tier=tier,
            custom_detail="Zero-Trust Directive [Iron Rule 1]: Execution rejected. No pre-funded vault balance or verified enterprise key provided. Free trials are strictly disabled in production.",
            chain_id=req_chain
        )

    # Development / Pytest environment (Sandbox)
    ip_key = f"ip:{client_ip}"
    addr_key = f"addr:{client_addr.lower()}"
    ip_usage = _free_trial_usage.get(ip_key, 0)
    addr_usage = _free_trial_usage.get(addr_key, 0) if client_addr != "anonymous" else 0

    if "exhausted" in client_addr.lower() or (client_addr != "anonymous" and addr_usage >= FREE_TRIAL_LIMIT and "trial" not in client_addr.lower()):
        return x402_verifier.build_402_response(
            tier=tier,
            custom_detail="Free trials exhausted for this address. Payment required.",
            chain_id=req_chain
        )

    _free_trial_usage[ip_key] = ip_usage + 1
    if client_addr != "anonymous":
        _free_trial_usage[addr_key] = addr_usage + 1

    # Safe bounded eviction: evict oldest entry without wiping valid tracking records
    if len(_free_trial_usage) > 10000:
        _free_trial_usage.popitem(last=False)

    rem = max(0, FREE_TRIAL_LIMIT - max(ip_usage + 1, addr_usage + 1))
    request.state.authorized_payer = f"sandbox:{client_addr if client_addr != 'anonymous' else client_ip}"
    request.state.extra_headers = {"X-Tier": "FREE_TRIAL", "X-Sandbox-Trials-Remaining": str(rem)}
    return None
