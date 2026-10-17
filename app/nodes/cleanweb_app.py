"""
Node 2: x402-Cleanweb-Agent Node App (Port 8002)
================================================
Enterprise-grade web content scrubbing, indirect prompt injection sanitization,
zero-width steganography stripping, and CSS hidden-text neutralization.
Includes SSRF protection for outbound URL purification.
"""

from __future__ import annotations

import ipaddress
import socket
import time
from typing import Any, Dict, Optional
from urllib.parse import urlparse
import urllib.request

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.cleanweb_sanitizer import cleanweb_sanitizer


app = FastAPI(
    title="x402-Cleanweb-Agent Oracle Node",
    version="2.0.0",
    description="Deterministic web scraper purification, hidden CSS injection neutralization, and data cleansing oracle with SSRF protection."
)

FORBIDDEN_HOSTS = {
    "localhost",
    "metadata.google.internal",
    "metadata",
    "169.254.169.254",
    "instance-data",
}


def is_safe_url(url: str) -> bool:
    """
    Validates whether a URL is safe to fetch from server-side.
    Rejects non-HTTP(S) schemes, localhost, private IP ranges, and cloud metadata services.
    """
    try:
        parsed = urlparse(url)
        scheme = parsed.scheme.lower()
        if scheme not in ("http", "https"):
            return False

        hostname = parsed.hostname
        if not hostname:
            return False

        hostname = hostname.lower()

        # Check explicit forbidden hosts
        if hostname in FORBIDDEN_HOSTS or hostname.endswith(".internal"):
            return False

        # Attempt to parse hostname directly as IP
        try:
            ip = ipaddress.ip_address(hostname)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
                return False
        except ValueError:
            # Hostname is a domain name, resolve DNS
            try:
                addr_info = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
                for family, _, _, _, sockaddr in addr_info:
                    ip_str = sockaddr[0]
                    resolved_ip = ipaddress.ip_address(ip_str)
                    if (
                        resolved_ip.is_private
                        or resolved_ip.is_loopback
                        or resolved_ip.is_link_local
                        or resolved_ip.is_reserved
                        or resolved_ip.is_multicast
                    ):
                        return False
            except Exception:
                return False

        return True
    except Exception:
        return False


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "node": "CLEANWEB_ORACLE",
        "port": 8002,
        "version": "2.0.0",
        "capabilities": [
            "HIDDEN_CSS_INJECTION_STRIPPING",
            "ZERO_WIDTH_STEGANOGRAPHY_REMOVAL",
            "MARKDOWN_COVERT_EXFIL_NEUTRALIZATION",
            "HOMOGLYPH_EVASION_NORMALIZATION",
            "PROMPT_INJECTION_REDACTION",
            "SSRF_PROTECTED_OUTBOUND_FETCH"
        ]
    }


@app.post("/clean")
@app.post("/verify")
async def clean_content(request: Request):
    """
    Sanitizes raw text or scraped HTML content.
    Extracts and strips hidden CSS injection, zero-width evasion, and exfiltration links.
    """
    body = await request.json()
    raw_content = body.get("content") or body.get("text") or body.get("html") or ""
    is_html = body.get("is_html")  # None triggers automatic HTML detection

    result = cleanweb_sanitizer.purify(raw_content=raw_content, is_html=is_html)
    return JSONResponse(content=result.to_dict())


@app.post("/purify-url")
async def purify_url(request: Request):
    """
    Purifies content associated with a URL.
    Accepts pre-fetched HTML or fetches raw webpage content safely and scrubs it.
    Guards against SSRF and cloud metadata access.
    """
    body = await request.json()
    url = body.get("url", "").strip()
    raw_html = body.get("html") or body.get("content") or ""

    # If raw HTML not provided, fetch safely if a valid HTTP URL
    if not raw_html and url:
        if not is_safe_url(url):
            return JSONResponse(
                status_code=400,
                content={
                    "status": "BLOCKED_SSRF",
                    "url": url,
                    "error": f"Blocked URL ({url}): Access to local/private network or cloud metadata services is prohibited."
                }
            )

        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "SecurityGate-CleanwebBot/2.0"}
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                raw_html = resp.read().decode("utf-8", errors="replace")
        except Exception as e:
            return JSONResponse(
                status_code=400,
                content={
                    "status": "FETCH_FAILED",
                    "url": url,
                    "error": f"Failed to retrieve URL content: {str(e)}"
                }
            )

    result = cleanweb_sanitizer.purify(raw_content=raw_html, is_html=True)
    res_dict = result.to_dict()
    res_dict["source_url"] = url
    return JSONResponse(content=res_dict)
