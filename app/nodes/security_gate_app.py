"""
Node 1: Security-Gate-x402 Node App (Port 8001)
===============================================
Deterministic AST / DLP filtering, prompt injection defense, and EIP-712 SafetyAttestation.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.main import app as main_app

# Re-export main_app as app
app = main_app

@app.get("/health")
async def health_check():
    return {"status": "healthy", "node": "SECURITY_GATE", "port": 8001}
