"""
Node 4: Minerals Oracle Node App (Port 8004)
============================================
Critical minerals pricing spread, RMI conformant smelter verification, and trade escrow calldata.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.truth_adapters.minerals_truth_adapter import minerals_truth_adapter

app = FastAPI(title="Minerals Oracle Node")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "node": "MINERALS_ORACLE", "port": 8004}

@app.post("/verify")
async def verify_minerals(request: Request):
    body = await request.json()
    job_id = body.get("job_id", "0x" + "22" * 32)
    mineral = body.get("mineral_type", "copper")
    smelter_id = body.get("smelter_id", "SMR-CHL-00921")
    smelter_status = body.get("smelter_audit_status", "CONFORMANT")
    mine_country = body.get("mine_country_code", "CL")
    coc_verified = bool(body.get("chain_of_custody_verified", True))
    child_labor_free = bool(body.get("child_labor_free", True))

    res = minerals_truth_adapter.verify_minerals_truth(
        job_id=job_id,
        mineral_type=mineral,
        smelter_id=smelter_id,
        smelter_audit_status=smelter_status,
        mine_country_code=mine_country,
        chain_of_custody_verified=coc_verified,
        child_labor_free=child_labor_free
    )
    return res
