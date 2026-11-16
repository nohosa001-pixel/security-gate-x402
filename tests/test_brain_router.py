from fastapi.testclient import TestClient

from app.brain_trainer import SecurityGateBrainTrainer
from app.main import app
from app.routers import brain as brain_router_module


def test_brain_status_and_cycle_endpoints(tmp_path, monkeypatch):
    isolated_trainer = SecurityGateBrainTrainer(state_dir=tmp_path)
    monkeypatch.setattr(brain_router_module, "_brain_trainer", isolated_trainer)

    client = TestClient(app)

    # 1. Cold-start GET /api/v1/brain/status auto-runs 1 initial cycle
    resp = client.get("/api/v1/brain/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["agent_identity"] == "agrid-security-gate-elizaos-brain-v1"
    assert data["total_cycles_completed"] == 1
    assert data["pull_sync_ready"] is True
    assert data["last_cycle"]["verdicts"]["security_blocked"] is True

    # 2. POST /api/v1/brain/cycle?cycles=2 advances 2 more cycles
    cycle_resp = client.post("/api/v1/brain/cycle?cycles=2")
    assert cycle_resp.status_code == 200
    c_data = cycle_resp.json()
    assert c_data["status"] == "success"
    assert c_data["executed_cycles"] == 2
    assert c_data["brain_status"]["total_cycles_completed"] == 3
