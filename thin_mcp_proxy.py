"""
agent-security-gate-x402 v3.0.0 Cloud-Native Thin MCP Proxy
===========================================================
Forwards local stdio MCP JSON-RPC 2.0 requests directly to the live
Security Gate x402 Cloud Run Gateway over HTTPS, ensuring:
- Zero local server dependencies (no fastapi, uvicorn, web3, eth-account, cryptography)
- Real-time <5ms prompt injection, AST, and ERC-20 approve/permit drain rules
- Transparent x402 / Agent Vault header forwarding
"""

from __future__ import annotations

import asyncio
import json
import os
import secrets
import sys
from typing import Any, Dict, Optional

import httpx

DEFAULT_GATEWAY_URL = os.getenv(
    "SECURITY_GATE_GATEWAY_URL",
    "https://agent-security-gate-x402-212942243360.asia-northeast3.run.app",
).rstrip("/")


def is_thin_client_mode() -> bool:
    """Returns True when running in v3.0.0 Thin Client mode or when local app.security_engine is absent."""
    flag = os.getenv("SECURITY_GATE_THIN_CLIENT", "").strip().lower()
    if flag in ("1", "true", "yes"):
        return True
    if flag in ("0", "false", "no"):
        return False
    try:
        import app.security_engine  # noqa: F401
        return False
    except ImportError:
        return True


def build_gateway_headers() -> Dict[str, str]:
    headers: Dict[str, str] = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "agent-security-gate-x402-thin/3.0.0",
        "X-Request-ID": f"sg_thin_{secrets.token_hex(6)}",
    }
    vault_key = os.getenv("AGENT_VAULT_KEY") or os.getenv("SECURITY_GATE_VAULT_KEY")
    if vault_key:
        headers["X-Vault-Key"] = vault_key
        headers["X-Agent-Pass"] = vault_key
    x402_sig = os.getenv("X402_SIGNATURE")
    if x402_sig:
        headers["X-402-Signature"] = x402_sig
    return headers


async def forward_jsonrpc_to_gateway(
    req_data: Dict[str, Any],
    gateway_url: Optional[str] = None,
    timeout_sec: float = 15.0,
) -> Optional[Dict[str, Any]]:
    """Forwards a JSON-RPC 2.0 MCP request to the Security Gate Cloud Gateway /mcp endpoint."""
    method = req_data.get("method", "")
    req_id = req_data.get("id")

    if method.startswith("notifications/") or req_id is None:
        return None

    if method == "ping":
        return {"jsonrpc": "2.0", "id": req_id, "result": {}}

    base = (gateway_url or DEFAULT_GATEWAY_URL).rstrip("/")
    mcp_endpoint = f"{base}/mcp"

    try:
        async with httpx.AsyncClient(timeout=timeout_sec) as client:
            resp = await client.post(mcp_endpoint, json=req_data, headers=build_gateway_headers())
            if resp.status_code == 402:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {
                        "code": -32002,
                        "message": (
                            f"x402 Payment Required. Pre-fund your Agent Vault at {base}/docs "
                            "and set AGENT_VAULT_KEY, or attach X-402-Signature."
                        ),
                    },
                }
            resp.raise_for_status()
            return resp.json()
    except Exception as exc:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {
                "code": -32603,
                "message": f"Security Gate Cloud Gateway error: {exc}",
            },
        }


async def run_thin_stdio_server() -> None:
    loop = asyncio.get_running_loop()
    while True:
        line_bytes = await loop.run_in_executor(None, sys.stdin.readline)
        if not line_bytes:
            break
        line_str = line_bytes.strip()
        if not line_str:
            continue
        try:
            req_data = json.loads(line_str)
            response = await forward_jsonrpc_to_gateway(req_data)
            if response is not None:
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()
        except Exception as exc:
            err_resp = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": f"Parse error: {exc}"},
            }
            sys.stdout.write(json.dumps(err_resp) + "\n")
            sys.stdout.flush()


def main() -> None:
    try:
        asyncio.run(run_thin_stdio_server())
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass


if __name__ == "__main__":
    main()
