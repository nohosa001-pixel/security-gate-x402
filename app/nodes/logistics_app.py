"""
Node 5: Logistics Oracle Node App (Port 8005)
=============================================
DCSA eBL v3.0, ISO 6346 container validation, telemetry Merkle Root, and EIP-712 PoD issuance.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from logistics_oracle_mcp import default_engine

app = FastAPI(title="Logistics Oracle Node")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "node": "LOGISTICS_ORACLE", "port": 8005}

@app.post("/verify_ebl")
async def verify_ebl(request: Request):
    body = await request.json()
    return default_engine.verify_dcsa_ebl(
        bl_number=body.get("blNumber", ""),
        carrier_scac=body.get("carrierScac", ""),
        vessel_imo=int(body.get("vesselImo", 0)),
        container_id=body.get("containerId", ""),
        origin_port=body.get("originPort", ""),
        dest_port=body.get("destPort", "")
    )

@app.post("/audit_telemetry")
async def audit_telemetry(request: Request):
    body = await request.json()
    return default_engine.audit_telemetry(
        sensor_logs=body.get("sensorLogs", []),
        max_allowed_temp_c=float(body.get("maxAllowedTempC", 25.0)),
        min_allowed_temp_c=float(body["minAllowedTempC"]) if "minAllowedTempC" in body else None
    )

@app.post("/issue_pod")
async def issue_pod(request: Request):
    body = await request.json()
    return default_engine.issue_pod_attestation(
        deal_id_hex=body.get("dealId", ""),
        bl_doc_hash=body.get("blDocumentHash", ""),
        container_id=body.get("containerId", ""),
        vessel_imo=int(body.get("vesselImo", 0)),
        dest_unlocode=body.get("destUnlocode", ""),
        sensor_logs=body.get("sensorLogs", []),
        max_allowed_temp_c=float(body.get("maxAllowedTempC", 25.0)),
        min_allowed_temp_c=float(body["minAllowedTempC"]) if "minAllowedTempC" in body else None
    )
