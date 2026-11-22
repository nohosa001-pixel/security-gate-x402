"""Unit tests for agent-security-gate-x402 v3.0.0 Thin MCP Proxy."""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from thin_mcp_proxy import (
    build_gateway_headers,
    forward_jsonrpc_to_gateway,
    is_thin_client_mode,
)


def test_is_thin_client_mode_env_override(monkeypatch):
    monkeypatch.setenv("SECURITY_GATE_THIN_CLIENT", "1")
    assert is_thin_client_mode() is True
    monkeypatch.setenv("SECURITY_GATE_THIN_CLIENT", "0")
    assert is_thin_client_mode() is False


def test_build_gateway_headers_with_vault_and_sig(monkeypatch):
    monkeypatch.setenv("AGENT_VAULT_KEY", "vault_test_123")
    monkeypatch.setenv("X402_SIGNATURE", "0xdeadbeef")
    headers = build_gateway_headers()
    assert headers["X-Vault-Key"] == "vault_test_123"
    assert headers["X-Agent-Pass"] == "vault_test_123"
    assert headers["X-402-Signature"] == "0xdeadbeef"
    assert headers["User-Agent"] == "agent-security-gate-x402-thin/3.0.0"


@pytest.mark.asyncio
async def test_forward_ping_and_notification():
    ping_res = await forward_jsonrpc_to_gateway({"jsonrpc": "2.0", "id": 7, "method": "ping"})
    assert ping_res == {"jsonrpc": "2.0", "id": 7, "result": {}}

    notif_res = await forward_jsonrpc_to_gateway({"jsonrpc": "2.0", "method": "notifications/initialized"})
    assert notif_res is None


@pytest.mark.asyncio
async def test_forward_tools_list_success():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {"jsonrpc": "2.0", "id": 1, "result": {"tools": [{"name": "verify_agent_output"}]}}

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = False
    mock_client.post.return_value = mock_resp

    with patch("thin_mcp_proxy.httpx.AsyncClient", return_value=mock_client):
        res = await forward_jsonrpc_to_gateway({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}})
        assert res["result"]["tools"][0]["name"] == "verify_agent_output"


@pytest.mark.asyncio
async def test_forward_402_payment_required():
    mock_resp = MagicMock()
    mock_resp.status_code = 402

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = False
    mock_client.post.return_value = mock_resp

    with patch("thin_mcp_proxy.httpx.AsyncClient", return_value=mock_client):
        res = await forward_jsonrpc_to_gateway({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {}})
        assert res["error"]["code"] == -32002
        assert "AGENT_VAULT_KEY" in res["error"]["message"]
