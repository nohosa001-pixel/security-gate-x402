import json
from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


def test_mcp_app_initialize_and_resources():
    r = client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
    assert r.status_code == 200
    body = r.json()["result"]
    assert "resources" in body["capabilities"]
    assert "tools" in body["capabilities"]

    rl = client.post("/mcp", json={"jsonrpc": "2.0", "id": 2, "method": "resources/list", "params": {}})
    assert rl.status_code == 200
    resources = rl.json()["result"]["resources"]
    assert len(resources) == 1
    assert resources[0]["uri"] == "ui://agrid/verdict-card.html"
    assert resources[0]["mimeType"] == "text/html;profile=mcp-app"

    rr = client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 3,
            "method": "resources/read",
            "params": {"uri": "ui://agrid/verdict-card.html"},
        },
    )
    assert rr.status_code == 200
    contents = rr.json()["result"]["contents"]
    assert len(contents) == 1
    assert contents[0]["mimeType"] == "text/html;profile=mcp-app"
    html = contents[0]["text"]
    assert "<!DOCTYPE html>" in html
    assert "ui/initialize" in html
    assert len(html.encode("utf-8")) < 10 * 1024 * 1024


def test_mcp_app_tools_meta_and_free_dashboard_entrypoint():
    tl = client.post("/mcp", json={"jsonrpc": "2.0", "id": 4, "method": "tools/list", "params": {}})
    assert tl.status_code == 200
    tools = {t["name"]: t for t in tl.json()["result"]["tools"]}

    for name in (
        "inspect_agent_output",
        "verify_agent_output",
        "inspect_code_ast_safety",
        "verify_counterparty_kyw_solvency",
    ):
        assert tools[name]["_meta"]["ui"]["resourceUri"] == "ui://agrid/verdict-card.html"

    dash_tool = tools["open_agrid_security_dashboard"]
    assert dash_tool["_meta"]["ui"]["resourceUri"] == "ui://agrid/verdict-card.html"
    entrypoints = dash_tool["_meta"]["com.google.antigravity/ui"]["entrypoints"]
    types = {ep["type"] for ep in entrypoints}
    assert types == {"aux_pane", "global"}

    # Dashboard entrypoint must succeed with empty args {} and zero 402 payment wall
    call = client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {"name": "open_agrid_security_dashboard", "arguments": {}},
        },
    )
    assert call.status_code == 200
    res = call.json()["result"]
    assert "structuredContent" in res
    assert res["structuredContent"]["view"] == "dashboard"
    assert res["structuredContent"]["status"] == "ONLINE"
    parsed = json.loads(res["content"][0]["text"])
    assert parsed["view"] == "dashboard"
