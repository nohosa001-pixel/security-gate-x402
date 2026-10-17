"""
Node 2: x402-Cleanweb-Agent Node App (Port 8002)
================================================
Enterprise-grade web content scrubbing, indirect prompt injection sanitization,
zero-width steganography stripping, and CSS hidden-text neutralization.
"""

from __future__ import annotations

import time
from typing import Any, Dict, Optional

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.cleanweb_sanitizer import cleanweb_sanitizer


app = FastAPI(
    title="x402-Cleanweb-Agent Oracle Node",
    version="2.0.0",
    description="Deterministic web scraper purification, hidden CSS injection neutralization, and data cleansing oracle."
)


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
            "PROMPT_INJECTION_REDACTION"
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
    """
    body = await request.json()
    url = body.get("url", "")
    raw_html = body.get("html") or body.get("content") or ""

    # If raw HTML not provided, fetch safely if a valid HTTP URL
    if not raw_html and url.startswith(("http://", "https://")):
        try:
            import urllib.request
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "SecurityGate-CleanwebBot/2.0 (+https://security-gate-x402.com)"}
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
