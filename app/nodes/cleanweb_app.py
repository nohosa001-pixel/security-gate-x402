"""
Node 2: x402-Cleanweb-Agent Node App (Port 8002)
================================================
Web content scrubbing, indirect prompt injection sanitization, and data cleansing.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.security_engine import audit_payload

app = FastAPI(title="x402-Cleanweb-Agent Node")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "node": "CLEANWEB_ORACLE", "port": 8002}

@app.post("/clean")
@app.post("/verify")
async def clean_content(request: Request):
    body = await request.json()
    text = body.get("text", "")
    audit = audit_payload(text=text, is_code=False)
    # Strip potential injected patterns
    cleaned = text
    if audit.threats:
        for threat in audit.threats:
            cleaned = cleaned.replace(threat, "[REDACTED_BY_CLEANWEB]")

    return {
        "status": "SUCCESS",
        "node": "cleanweb",
        "risk_score": audit.risk_score,
        "threats_detected": audit.threats,
        "sanitized_output": cleaned
    }
