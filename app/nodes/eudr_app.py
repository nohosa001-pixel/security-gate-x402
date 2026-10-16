"""
Node 3: EUDR Compliance Oracle Node App (Port 8003)
===================================================
EU Deforestation-Free Regulation (GeoJSON polygon & TRACES-NT) verification.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.truth_adapters.eudr_truth_adapter import eudr_truth_adapter

app = FastAPI(title="EUDR Compliance Oracle Node")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "node": "EUDR_ORACLE", "port": 8003}

@app.post("/verify")
async def verify_eudr(request: Request):
    body = await request.json()
    job_id = body.get("job_id", "0x" + "11" * 32)
    commodity = body.get("commodity", "wood")
    country_code = body.get("country_code", "CD")
    polygon = body.get("polygon_coordinates", [(-3.1, 29.8), (-3.2, 29.9), (-3.1, 29.8)])
    dds_ref = body.get("dds_reference_id", "DDS-EUDR-2026")

    res = eudr_truth_adapter.verify_eudr_truth(
        job_id=job_id,
        commodity=commodity,
        country_code=country_code,
        polygon_coordinates=polygon,
        dds_reference_id=dds_ref
    )
    return res
