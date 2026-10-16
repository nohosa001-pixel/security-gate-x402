"""
Node 7: Zero-Knowledge Credential Egress Proxy App (Port 8080)
==============================================================
Sole egress gateway authorized to communicate with external APIs and blockchain RPCs.
Hot-swaps {{ZK_REF::...}} placeholder tokens with real credentials stored in memory.
"""

import os
import re
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
import httpx
from app.proxy_vault import ZeroExposureProxyVault

app = FastAPI(title="Zero-Knowledge Credential Egress Proxy")
vault = ZeroExposureProxyVault()

# Load and register secrets from environment
SECRETS_MAP = {
    "EUDR_TRACES_API_KEY": os.environ.get("EUDR_TRACES_API_KEY", "mock_traces_key"),
    "MINERALS_FEED_API_KEY": os.environ.get("MINERALS_FEED_API_KEY", "mock_lme_key"),
    "AIS_MARITIME_API_KEY": os.environ.get("AIS_MARITIME_API_KEY", "mock_ais_key"),
}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "node": "ZK_EGRESS_PROXY", "port": 8080}

@app.post("/forward")
async def forward_request(request: Request):
    body = await request.body()
    text = body.decode("utf-8", errors="ignore")

    # Replace ZK placeholder handles with actual secrets in outbound packet
    for secret_name, secret_val in SECRETS_MAP.items():
        placeholder = f"{{{{ZK_REF::{secret_name}}}}}"
        if placeholder in text:
            text = text.replace(placeholder, secret_val)

    target_url = request.headers.get("X-Target-Url")
    if not target_url:
        return {"status": "SCRUBBED_AND_SUBMITTED", "data_len": len(text)}

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.post(target_url, content=text.encode("utf-8"))
            return Response(content=resp.content, status_code=resp.status_code, media_type=resp.headers.get("content-type"))
        except Exception as e:
            return JSONResponse(status_code=502, content={"error": f"Upstream failure: {str(e)}"})
