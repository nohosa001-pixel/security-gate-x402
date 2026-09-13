# ⚡ 3-Minute Quickstart Guide: Protect Any AI Agent

> **"Give your autonomous agent a bulletproof security radar and financial spend guardrails in under 3 minutes."**

The Sheriff of Agent Finance (`agent-security-gate-x402`) provides **sub-5ms deterministic prompt injection defense**, **malicious AST code sandboxing**, **factual hallucination verification**, and **EIP-191/EIP-712 cryptographic audit proofs** for EVM smart contracts.

---

## 🚀 Option 1: Python / LangChain / CrewAI (3 Lines of Code)

### Step 1. Install Package

```bash
pip install agent-security-gate-x402
```

### Step 2. Add Guard to Your Agent

```python
from sdk import SecurityGateClient, SecurityGateBlockedError

# Connects directly to the live Google Cloud Run micro-oracle
gate = SecurityGateClient()

# Inspect any LLM text, prompt, or tool output
try:
    report = gate.inspect("Agent executed order: 50 USDC swap.")
    print("✅ Passed:", report["audit"]["verdict"])
except SecurityGateBlockedError as err:
    print("🚨 Blocked threat:", err.verdict, err.risk_score)
```

### Step 3. Protect Autonomous Wallets Against Infinite Budget Drain

```python
from sdk import BoundedAgentWallet, SecurityGateClient

# Enforce strict financial guardrails
wallet = BoundedAgentWallet(
    per_tx_limit_usdc=0.05,  # Max $0.05 per API call
    daily_limit_usdc=1.00,   # Hard daily stop of $1.00
    whitelist=["0x255F9991233f86B29dB847c8d5b8CB9915e80dCf"]
)

gate = SecurityGateClient(bounded_wallet=wallet)
```

---

## 🤖 Option 2: 1-Click MCP Setup (Claude Desktop & Cursor)

No code required. Connect directly to Claude Desktop, Cursor IDE, or Windsurf via Model Context Protocol:

### Cursor IDE Setup

1. Open **Cursor Settings** (`Ctrl + ,` or `Cmd + ,`) → Navigate to **Features** → **MCP Servers**.
2. Click **Add New MCP Server**.
3. Set **Type**: `command`
4. Set **Name**: `security-gate-x402`
5. Set **Command**: `uvx agent-security-gate-x402`

### Claude Desktop Setup

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "security-gate-x402": {
      "command": "uvx",
      "args": ["agent-security-gate-x402"]
    }
  }
}
```

---

## 🌐 Option 3: ElizaOS / TypeScript / Node.js Agents

Drop our TypeScript evaluator into your ElizaOS character actions:

```typescript
import { SecurityGateEvaluator } from "./examples/elizaos_security_plugin";

const gate = new SecurityGateEvaluator();

// Inspect proposal before dispatching web3 transaction
const verdict = await gate.inspect(
  "Action: buyToken | token: 0x... | amount: 1000"
);

if (verdict.status === "PASSED") {
  console.log("Verified safe with zero-liability proof:", verdict.audit_proof);
}
```

---

## 🛠️ Interactive Web Sandbox & Live Endpoints

Test immediately in your browser without installing anything:

* 🖥️ **Live Web Dashboard & Simulator**: [https://agent-security-gate-x402-212942243360.asia-northeast3.run.app/dashboard](https://agent-security-gate-x402-212942243360.asia-northeast3.run.app/dashboard)
* ⚡ **Browser Playground**: [https://agent-security-gate-x402-212942243360.asia-northeast3.run.app/playground](https://agent-security-gate-x402-212942243360.asia-northeast3.run.app/playground)
* 📖 **OpenAPI / Swagger Docs**: [https://agent-security-gate-x402-212942243360.asia-northeast3.run.app/docs](https://agent-security-gate-x402-212942243360.asia-northeast3.run.app/docs)
