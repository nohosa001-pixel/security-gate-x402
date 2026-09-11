"""
Tests for A.GRID Ops Central Hub Clearinghouse Client Integration in Security Gate x402.
Verifies asynchronous, non-blocking dispatch of micropayment clearing events
to the central agrid-ops-agent headquarters.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.agrid_ops_client import (
    report_clearing_event_async,
    dispatch_clearing_event_background
)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.mark.asyncio
async def test_report_clearing_event_payload_structure():
    """Verifies the JSON payload schema matches A.GRID clearinghouse requirements."""
    mock_response = MagicMock()
    mock_response.is_success = True
    mock_response.json.return_value = {
        "status": "CLEARED",
        "journal_entry_id": "JE-2026-0001",
        "amount_krw": 3
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response

        res = await report_clearing_event_async(
            operation="/api/v1/inspect",
            amount_usdc=0.002,
            caller_agent_id="0xAgentTestAddress",
            source_service="security-gate",
            chain="polygon"
        )

        assert res is not None
        assert res["status"] == "CLEARED"
        assert mock_post.called

        call_args = mock_post.call_args
        assert "/api/v1/grid/clearing/event" in call_args[0][0]
        payload = call_args[1]["json"]
        assert payload["source_service"] == "security-gate"
        assert payload["amount_usdc"] == 0.002
        assert payload["caller_agent_id"] == "0xAgentTestAddress"
        assert payload["operation"] == "/api/v1/inspect"
        assert payload["chain"] == "polygon"


@pytest.mark.asyncio
async def test_report_clearing_event_graceful_offline_fallback():
    """Ensures Security Gate never fails or raises exceptions if central ops agent is offline."""
    with patch("httpx.AsyncClient.post", side_effect=Exception("Connection refused (HQ offline)")):
        res = await report_clearing_event_async(
            operation="/api/v1/inspect",
            amount_usdc=0.002,
            caller_agent_id="0xOfflinePayer"
        )
        # Must return None safely without raising an unhandled exception
        assert res is None


def test_inspection_triggers_clearing_dispatch(client):
    """Verifies that inspecting with x402 payment header triggers clearing event dispatch."""
    with patch("app.agrid_ops_client.dispatch_clearing_event_background") as mock_dispatch:
        headers = {
            "Authorization-x402": "x402_test_sig",
            "X-Client-Address": "0x1111111111111111111111111111111111111111"
        }
        resp = client.post(
            "/api/v1/inspect",
            json={"agent_output": "Safe agent code: print('hello world')"},
            headers=headers
        )

        assert resp.status_code == 200
        assert mock_dispatch.called
        call_kwargs = mock_dispatch.call_args.kwargs
        assert call_kwargs["operation"] == "x402_inspection"
        assert call_kwargs["amount_usdc"] == 0.002
        assert call_kwargs["caller_agent_id"] == "0x1111111111111111111111111111111111111111"
