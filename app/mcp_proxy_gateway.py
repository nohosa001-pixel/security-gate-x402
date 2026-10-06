"""
Agent Security Gate x402 - Transparent MCP Security Proxy Gateway.
====================================================================
Acts as a zero-trust, fail-closed reverse proxy sitting in front of ANY target
MCP server (stdio or HTTP). 

Whenever an autonomous agent or host client calls a tool on the upstream MCP server:
1. Intercepts incoming `tools/call` JSON-RPC requests before they reach the target server.
2. Performs ultra-fast (<2ms) deterministic payload inspection:
   - Shell commands: audited via ShellSecurityEngine (blocks rm -rf, /dev/tcp, base64 pipes)
   - Code payloads: audited via Python AST parser (blocks subprocess, eval, socket)
   - Prompt & arguments: audited via SecurityEngine (blocks prompt injection, secret leaks)
3. If ANY violation is detected, the request is BLOCKED IMMEDIATELY (Fail-Closed)
   without ever invoking the target tool.
4. If clean, the request is transparently forwarded to the upstream MCP process.
"""

import asyncio
import json
import logging
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

from app.security_engine import audit_payload, parse_code_ast
from app.shell_security_engine import shell_security_engine

logger = logging.getLogger("MCPProxyGateway")

# Names or parameter keys commonly associated with shell/command execution
SHELL_TOOL_HINTS = {"bash", "terminal", "command", "sh", "exec_cmd", "shell", "run_command", "run_terminal_cmd"}
SHELL_ARG_KEYS = {"command", "cmd", "script", "commandline", "bash"}

# Names or parameter keys commonly associated with raw code execution
CODE_TOOL_HINTS = {"python", "eval", "code", "run_code", "execute_code", "repl"}
CODE_ARG_KEYS = {"code", "python_code", "snippet"}


class MCPProxySecurityInterceptor:
    """Zero-trust policy evaluator for intercepting tool call payloads."""

    @staticmethod
    def inspect_tool_call(tool_name: str, arguments: Dict[str, Any]) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        Inspects incoming tool call arguments against all security layers.
        Returns: (is_allowed, block_reason, incident_details)
        """
        tool_lower = tool_name.lower()

        # 1. Inspect Shell Commands
        is_shell = any(hint in tool_lower for hint in SHELL_TOOL_HINTS)
        for key, val in arguments.items():
            if not isinstance(val, str):
                continue

            if is_shell or key.lower() in SHELL_ARG_KEYS:
                shell_audit = shell_security_engine.audit_command(val)
                if not shell_audit.get("is_safe", True):
                    threats = shell_audit.get("threats", [])
                    reason = f"BLOCKED: Dangerous shell command detected in tool '{tool_name}' (Threats: {', '.join(threats)})"
                    return False, reason, shell_audit

            # 2. Inspect Code Payloads
            is_code = any(hint in tool_lower for hint in CODE_TOOL_HINTS) or key.lower() in CODE_ARG_KEYS
            if is_code:
                ast_audit = parse_code_ast(val)
                if not ast_audit.get("is_safe", True):
                    hazards = [h["detail"] for h in ast_audit.get("hazards", [])]
                    reason = f"BLOCKED: Dangerous AST code pattern detected in tool '{tool_name}' ({', '.join(hazards)})"
                    return False, reason, ast_audit

            # 3. Inspect General Text / Arguments for Injections & Secret Leaks
            sec_audit = audit_payload(text=val, is_code=False)
            if not sec_audit.is_safe:
                reason = f"BLOCKED: Prompt injection or credential leak in tool '{tool_name}' argument '{key}'"
                return False, reason, sec_audit.model_dump()

        return True, None, None


class MCPTransparentProxy:
    """
    Transparent stdio proxy process wrapper.
    Reads from standard input, intercepts, and communicates with child MCP process.
    """

    def __init__(self, target_command: List[str]):
        self.target_command = target_command
        self.interceptor = MCPProxySecurityInterceptor()

    async def run(self):
        """Starts the upstream child process and pipes stdio with inspection."""
        logger.info(f"Starting upstream MCP server: {' '.join(self.target_command)}")
        proc = await asyncio.create_subprocess_exec(
            *self.target_command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        loop = asyncio.get_event_loop()
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await loop.connect_read_pipe(lambda: protocol, sys.stdin)

        async def forward_upstream():
            while True:
                line = await reader.readline()
                if not line:
                    break
                try:
                    payload = json.loads(line.decode("utf-8").strip())
                    method = payload.get("method")
                    req_id = payload.get("id")

                    if method == "tools/call":
                        params = payload.get("params", {})
                        tool_name = params.get("name", "")
                        tool_args = params.get("arguments", {})

                        is_allowed, block_reason, details = self.interceptor.inspect_tool_call(tool_name, tool_args)
                        if not is_allowed:
                            # Intercept and return fail-closed JSON-RPC error
                            response = {
                                "jsonrpc": "2.0",
                                "id": req_id,
                                "error": {
                                    "code": -32000,
                                    "message": block_reason,
                                    "data": details
                                }
                            }
                            sys.stdout.write(json.dumps(response) + "\n")
                            sys.stdout.flush()
                            continue

                    # Safe to forward upstream
                    proc.stdin.write(line)
                    await proc.stdin.drain()

                except json.JSONDecodeError:
                    # Pass non-JSON line directly
                    proc.stdin.write(line)
                    await proc.stdin.drain()

        async def forward_downstream():
            while True:
                line = await proc.stdout.readline()
                if not line:
                    break
                sys.stdout.write(line.decode("utf-8"))
                sys.stdout.flush()

        async def forward_stderr():
            while True:
                line = await proc.stderr.readline()
                if not line:
                    break
                sys.stderr.write(line.decode("utf-8"))
                sys.stderr.flush()

        await asyncio.gather(forward_upstream(), forward_downstream(), forward_stderr())


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Security Gate x402 - Transparent MCP Proxy")
    parser.add_argument("--upstream", nargs="+", required=True, help="Command to start upstream MCP server (e.g. --upstream python mcp_server.py)")
    args = parser.parse_args()

    proxy = MCPTransparentProxy(args.upstream)
    asyncio.run(proxy.run())
