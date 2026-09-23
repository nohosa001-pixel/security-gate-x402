"""
Outbound Covert-Channel & Data Loss Prevention (DLP) Filter.
Intercepts outbound autonomous agent outputs, trade instructions, or LLM responses
to block:
1. Markdown and HTML covert image exfiltration channels (e.g. ![leak](https://...?k=...))
2. EVM raw private keys, BIP32 extended keys, and PEM certificates
3. Cloud credentials (AWS Access Keys, GitHub PATs)
"""

import re
import time
from typing import Any, Dict, List, Optional


class OutboundLeakBlockedError(Exception):
    """Raised when an outbound payload contains sensitive credentials or covert-channel exfiltration."""
    pass


COVERT_IMAGE_MD = re.compile(r"!\[.*?\]\((https?://[^\s\)]+)\)", re.IGNORECASE)
COVERT_IMAGE_HTML = re.compile(r"<img\s+[^>]*src=[\"'](https?:[^\"']+)[\"'][^>]*>", re.IGNORECASE)

SECRET_PATTERNS = [
    (
        re.compile(r"-----BEGIN\s+(RSA\s+|EC\s+)?PRIVATE\s+KEY-----", re.IGNORECASE),
        "Outbound Leak: Private Key PEM Structure",
        100,
    ),
    (
        re.compile(r"\b0x[a-fA-F0-9]{64}\b"),
        "Outbound Leak: EVM Raw Private Key / Seed Material",
        100,
    ),
    (
        re.compile(r"\b(AKIA|ABIA|ACCA|ASIA)[0-9A-Z]{16}\b"),
        "Outbound Leak: AWS Access Key ID",
        95,
    ),
    (
        re.compile(r"\bghp_[a-zA-Z0-9]{36}\b"),
        "Outbound Leak: GitHub Personal Access Token",
        95,
    ),
    (
        re.compile(r"xprv[a-zA-Z0-9]{107,108}"),
        "Outbound Leak: BIP32 Extended Private Key",
        100,
    ),
]


def inspect_outbound_payload(content: str) -> Dict[str, Any]:
    """
    Deterministically evaluates an outbound message or transaction metadata string.
    Returns audit dictionary with verdict, risk score, and detected threats.
    """
    start_time = time.time()
    text = content or ""
    threats: List[str] = []
    max_risk = 0

    # 1. Check for credential/key leaks
    for pattern, threat, risk in SECRET_PATTERNS:
        if pattern.search(text):
            threats.append(threat)
            max_risk = max(max_risk, risk)

    # 2. Check for covert Markdown image exfiltration
    for match in COVERT_IMAGE_MD.finditer(text):
        target_url = match.group(1)
        if re.search(r"(\?|&)(leak|token|key|secret|data|auth|wallet)=", target_url, re.IGNORECASE) or len(target_url) > 250:
            threats.append("Covert Channel: Markdown Image URL Data Exfiltration")
            max_risk = max(max_risk, 95)

    # 3. Check for covert HTML image exfiltration
    for match in COVERT_IMAGE_HTML.finditer(text):
        target_url = match.group(1)
        if re.search(r"(\?|&)(leak|token|key|secret|data|auth|wallet)=", target_url, re.IGNORECASE) or len(target_url) > 250:
            threats.append("Covert Channel: HTML Image Tag Data Exfiltration")
            max_risk = max(max_risk, 95)

    verdict = "ALLOW"
    sanitized_text: Optional[str] = None

    if max_risk >= 75:
        verdict = "BLOCK"
        sanitized_text = f"🚨 [SECURITY GATE: OUTBOUND LEAK BLOCKED] Intercepted hazards: {', '.join(threats)}"
    elif max_risk >= 30:
        verdict = "WARN"

    execution_time_ms = max(0.05, (time.time() - start_time) * 1000)

    return {
        "verdict": verdict,
        "risk_score": max_risk,
        "threats": threats,
        "sanitized_text": sanitized_text,
        "execution_time_ms": round(execution_time_ms, 3),
    }


def enforce_outbound_safety(content: str, raise_on_block: bool = True) -> str:
    """
    Enforces outbound DLP safety. Returns safe text or raises OutboundLeakBlockedError.
    """
    audit = inspect_outbound_payload(content)
    if audit["verdict"] == "BLOCK":
        if raise_on_block:
            raise OutboundLeakBlockedError(audit["sanitized_text"])
        return audit["sanitized_text"]
    return content
