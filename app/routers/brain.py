"""ElizaOS Brain Server Endpoints (Cloud Run + Pull Telemetry for A.GRID Ops)."""

from fastapi import APIRouter, Query
from app.brain_trainer import SecurityGateBrainTrainer

router = APIRouter(prefix="/api/v1/brain", tags=["ElizaOS Brain"])

_brain_trainer = SecurityGateBrainTrainer()


@router.get("/status", summary="Get ElizaOS Brain learning telemetry (A.GRID Ops Pull endpoint)")
async def get_brain_status():
    """Returns current 5-domain ElizaOS Brain readiness, Brier score, and latest cycle verdicts."""
    return _brain_trainer.get_status_summary()


@router.post("/cycle", summary="Execute ElizaOS Brain shadow learning cycle(s)")
async def run_brain_cycle(
    cycles: int = Query(default=1, ge=1, le=10, description="Number of shadow learning cycles to execute (1-10)")
):
    """Triggers 1..10 shadow learning cycles on Cloud Run (compatible with Cloud Scheduler 15m cron)."""
    results = [_brain_trainer.execute_training_cycle(mode="cloud_scheduler") for _ in range(cycles)]
    return {
        "status": "success",
        "executed_cycles": len(results),
        "latest_result": results[-1],
        "brain_status": _brain_trainer.get_status_summary(),
    }

