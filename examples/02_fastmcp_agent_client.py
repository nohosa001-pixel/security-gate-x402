"""Example 2: Invoking the Security Gate via Model Context Protocol (MCP) HTTP / JSON-RPC.

Compatible with Glama.ai, Claude Desktop, Cursor, and any MCP-compliant agent runtime.
"""

import json
import os
import sys
import httpx

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

LIVE_GATE_URL = "https://agent-security-gate-x402-7qxtp3324q-du.a.run.app"


def main():
    print("==================================================================")
    print("🛠️ [MCP DEMO] Discovering Tools and Invoking via JSON-RPC")
    print("==================================================================")

    with httpx.Client(base_url=LIVE_GATE_URL, timeout=10.0) as client:
        # 1. Discover Tools
        r_tools = client.get("/mcp/tools")
        print(f"📡 1. Discovered Tools from {LIVE_GATE_URL}/mcp/tools:")
        tools = r_tools.json().get("tools", [])
        for t in tools:
            print(f"   - Tool: {t['name']}")
            print(f"     Description: {t['description']}")

        # 2. Invoke Tool with Free Trial / x402 Header
        print("\n⚡ 2. Invoking 'inspect_agent_output' via POST /mcp/invoke...")
        mcp_payload = {
            "name": "inspect_agent_output",
            "arguments": {
                "agent_output": "Quarterly cloud migration: 48 instances transferred with 0 downtime.",
                "is_code": False,
                "context_ground_truth": "Ledger: 48 instances transferred with 0 downtime."
            }
        }

        r_invoke = client.post("/mcp/invoke", json=mcp_payload, headers={"X-Trial": "true"})
        print(f"   Response Status: {r_invoke.status_code}")
        
        result_json = r_invoke.json()
        content_text = result_json["content"][0]["text"]
        inspection_data = json.loads(content_text)

        print("\n📄 3. Tool Execution Result:")
        print(f"   Verdict: {inspection_data['audit']['verdict']}")
        print(f"   Risk Score: {inspection_data['audit']['risk_score']}")
        print(f"   Is Faithful: {inspection_data['audit']['nli_verification']['is_faithful']}")
        print(f"   Attestation Signature: {inspection_data['attestation']['signature'][:30]}...")
        print(f"   Payment Status: {inspection_data['pricing']['rate']}")


if __name__ == "__main__":
    main()
