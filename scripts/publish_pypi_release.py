#!/usr/bin/env python3
"""
Safely publishes agent-security-gate-x402 v2.1.0 to PyPI.
Zero secret exposure; reads token strictly from local .env.
"""

import os
import sys
import subprocess
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

token = (
    os.environ.get("UV_PUBLISH_TOKEN")
    or os.environ.get("TWINE_PASSWORD")
    or os.environ.get("PYPI_API_TOKEN")
)

if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

if not token:
    print("[ERROR] No PyPI token discovered in environment or .env file.")
    sys.exit(1)

dist_files = [
    f for f in ROOT_DIR.glob("dist/agent_security_gate_x402-2.1.0*")
    if f.suffix in [".gz", ".whl"]
]
if not dist_files:
    print("[ERROR] No v2.1.0 distribution files found in dist/.")
    sys.exit(1)

print(f"[*] Found {len(dist_files)} package artifacts for v2.1.0:")
for f in dist_files:
    print(f"  - {f.name} ({f.stat().st_size:,} bytes)")

env = os.environ.copy()
env["UV_PUBLISH_TOKEN"] = token

cmd = ["uv", "publish"] + [str(f) for f in dist_files]

print("\n🚀 Uploading agent-security-gate-x402 v2.1.0 to PyPI...")
res = subprocess.run(cmd, env=env, cwd=ROOT_DIR)

if res.returncode == 0:
    print("\n✅ PyPI v2.1.0 PUBLISH SUCCESSFUL!")
    print("📦 Live Package: https://pypi.org/project/agent-security-gate-x402/2.1.0/")
else:
    print(f"\n❌ Publish failed with exit code: {res.returncode}")
    sys.exit(res.returncode)
