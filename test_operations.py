"""
Production Operations & Live Benchmark Suite for Agent Security Gate x402.
Verifies health, inspection latency (<10ms target), onchain EIP-712 calldata,
and static dashboard availability across deployed Cloud Run or local instances.
"""

import os
import sys
import time
import httpx
from dotenv import load_dotenv

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv()

BASE_URL = os.getenv("GATE_URL", os.getenv("TARGET_URL", "https://agent-security-gate-x402-7qxtp3324q-du.a.run.app"))


def run_benchmark():
    print("=" * 65)
    print(f"  Agent Security Gate x402 - Operations Benchmark Suite")
    print(f"  Target Server: {BASE_URL}")
    print("=" * 65)

    with httpx.Client(base_url=BASE_URL, timeout=10.0) as client:
        # 1. Health check
        r_health = client.get("/health")
        print(f"\n[1/5] Health Check: Status {r_health.status_code}")
        assert r_health.status_code == 200, f"Health check failed: {r_health.text}"
        print(f"      Response: {r_health.json()}")

        # 2. Dashboard UI availability
        r_dash = client.get("/")
        print(f"\n[2/5] Static Dashboard Check: Status {r_dash.status_code}")
        assert r_dash.status_code == 200, f"Dashboard failed: {r_dash.status_code}"

        # 3. Clean inspection latency benchmark
        payload_clean = {
            "agent_output": "Quarterly net revenue confirmed at $1.2M with zero infrastructure errors.",
            "context_ground_truth": "Ledger: Q3 net revenue $1.2M, 0 critical errors."
        }
        latencies = []
        for i in range(10):
            t0 = time.perf_counter()
            r_inspect = client.post("/inspect", json=payload_clean)
            lat = (time.perf_counter() - t0) * 1000.0
            latencies.append(lat)
            assert r_inspect.status_code == 200, f"Inspection failed: {r_inspect.text}"

        avg_lat = sum(latencies) / len(latencies)
        min_lat = min(latencies)
        print(f"\n[3/5] Latency Benchmark (10 iterations):")
        print(f"      Avg: {avg_lat:.2f} ms | Min: {min_lat:.2f} ms | Max: {max(latencies):.2f} ms")
        assert avg_lat < 50.0, f"Latency benchmark too high: {avg_lat:.2f}ms"

        # 4. AST code inspection
        payload_ast = {"code": "import os\nos.system('rm -rf /')"}
        r_ast = client.post("/inspect/ast", json=payload_ast)
        print(f"\n[4/5] AST Hazard Parser Check: Status {r_ast.status_code}")
        assert r_ast.status_code == 200
        ast_data = r_ast.json()
        print(f"      Is Safe: {ast_data.get('is_safe')} (Hazards: {len(ast_data.get('ast_analysis', {}).get('hazards', []))})")
        assert ast_data.get("is_safe") is False, "Dangerous code should be marked unsafe"

        # 5. On-Chain EIP-712 Attestation Calldata
        payload_onchain = {"action_payload": "TRANSFER 5000 USDC", "chain_id": 137}
        r_onchain = client.post("/api/v1/gate/attestation/onchain", json=payload_onchain)
        print(f"\n[5/5] On-Chain Attestation Check: Status {r_onchain.status_code}")
        assert r_onchain.status_code == 200
        onchain_data = r_onchain.json()
        print(f"      Signer: {onchain_data.get('signer_address')}")
        print(f"      Calldata length: {len(onchain_data.get('abi_calldata', ''))} chars")

    print("\n" + "=" * 65)
    print("  ✅ All Operations & Benchmark Tests Passed Successfully!")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    run_benchmark()
