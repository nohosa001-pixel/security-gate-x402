"""
Unit tests for Autonomous Agent-Native Universal Exchange Engine (app/trade_engine.py).
Tests:
1. Pyth Hermes Oracle price resolution (with fallback guarantee).
2. Market BUY execution against DMM TreasuryVault.
3. Market SELL execution and asset quantity calculation.
4. Limit order boundary queuing (QUEUED_LIMIT_UNREACHED).
5. Trade history recording and settlement signature generation.
"""

import pytest
from app.trade_engine import (
    AgentTradeIntent,
    AgentExchangeSolver,
    DEPLOYED_CLEARING_HOUSE,
    DEPLOYED_TREASURY_VAULT,
    GATE_FEE_USDC
)


@pytest.fixture
def solver():
    return AgentExchangeSolver()


def test_oracle_price_feed(solver):
    """Verifies that the exchange retrieves valid prices for supported pairs."""
    for pair in ["ETH/USDC", "BTC/USDC", "SOL/USDC"]:
        info = solver.get_oracle_price(pair)
        assert "price" in info
        assert info["price"] > 0.0
        assert "source" in info
        assert "publish_time" in info


def test_market_buy_intent_settlement(solver):
    """Tests executing a market BUY intent settles atomically against TreasuryVault."""
    intent = AgentTradeIntent(
        agent_address="0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
        pair="ETH/USDC",
        direction="BUY",
        amount_usdc=100.0,
        intent_type="MARKET"
    )

    result = solver.solve_intent(intent)

    assert result.status == "SETTLED"
    assert result.pair == "ETH/USDC"
    assert result.direction == "BUY"
    assert result.amount_usdc == 100.0
    assert result.asset_qty > 0.0
    assert result.matched_price > 0.0
    assert result.counterparty == DEPLOYED_TREASURY_VAULT
    assert result.clearing_house == DEPLOYED_CLEARING_HOUSE
    assert result.gate_fee_usdc == GATE_FEE_USDC
    assert result.settlement_signature.startswith("0x")


def test_market_sell_intent_settlement(solver):
    """Tests executing a market SELL intent."""
    intent = AgentTradeIntent(
        agent_address="0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
        pair="SOL/USDC",
        direction="SELL",
        amount_usdc=50.0,
        intent_type="MARKET"
    )

    result = solver.solve_intent(intent)

    assert result.status == "SETTLED"
    assert result.pair == "SOL/USDC"
    assert result.direction == "SELL"
    assert result.asset_qty > 0.0


def test_limit_order_unreached(solver):
    """Tests that a limit BUY order far below current market price is queued."""
    oracle_info = solver.get_oracle_price("ETH/USDC")
    current_price = oracle_info["price"]

    # Set unrealistically low limit buy price (e.g. 50% of market price)
    unrealistic_limit = current_price * 0.5

    intent = AgentTradeIntent(
        agent_address="0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
        pair="ETH/USDC",
        direction="BUY",
        amount_usdc=50.0,
        intent_type="LIMIT",
        limit_price=unrealistic_limit
    )

    result = solver.solve_intent(intent)
    assert result.status == "QUEUED_LIMIT_UNREACHED"
    assert result.asset_qty == 0.0


def test_trade_history_recording(solver):
    """Verifies executed trades are preserved in recent trade queries."""
    intent = AgentTradeIntent(
        agent_address="0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
        pair="BTC/USDC",
        direction="BUY",
        amount_usdc=250.0,
        intent_type="MARKET"
    )
    solver.solve_intent(intent)

    recent = solver.get_recent_trades(limit=5)
    assert len(recent) >= 1
    assert recent[-1]["pair"] == "BTC/USDC"
    assert recent[-1]["amount_usdc"] == 250.0


def test_trade_api_endpoints():
    """Tests /api/v1/trade/intent, /api/v1/trade/price, and /api/v1/trade/orders via FastAPI TestClient."""
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)

    # 1. Price endpoint
    res_price = client.get("/api/v1/trade/price/ETH/USDC")
    assert res_price.status_code == 200
    price_data = res_price.json()
    assert "price" in price_data and price_data["price"] > 0

    # 2. Intent endpoint
    intent_payload = {
        "agent_address": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
        "pair": "ETH/USDC",
        "direction": "BUY",
        "amount_usdc": 15.0,
        "intent_type": "MARKET"
    }
    res_intent = client.post("/api/v1/trade/intent", json=intent_payload)
    assert res_intent.status_code == 200
    intent_data = res_intent.json()
    assert intent_data["status"] == "SETTLED"
    assert intent_data["pair"] == "ETH/USDC"
    assert intent_data["amount_usdc"] == 15.0

    # 3. Orders endpoint
    res_orders = client.get("/api/v1/trade/orders")
    assert res_orders.status_code == 200
    orders_data = res_orders.json()
    assert "orders" in orders_data
    assert len(orders_data["orders"]) >= 1

    # 4. MCP call endpoint
    mcp_payload = {
        "name": "submit_agent_trade_intent",
        "arguments": {
            "agent_address": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
            "pair": "SOL/USDC",
            "direction": "SELL",
            "amount_usdc": 30.0,
            "intent_type": "MARKET"
        }
    }
    res_mcp = client.post("/mcp/call", json=mcp_payload)
    assert res_mcp.status_code == 200
    mcp_res = res_mcp.json()
    assert "content" in mcp_res
    content_text = mcp_res["content"][0]["text"]
    assert "SETTLED" in content_text

