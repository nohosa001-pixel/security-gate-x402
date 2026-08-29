# Agent Output Security & Hallucination Gate (`agent-security-gate-x402`) 🛡️⚡

[![PyPI Version](https://img.shields.io/pypi/v/agent-security-gate-x402.svg?color=blue&style=for-the-badge&logo=pypi&logoColor=white)](https://pypi.org/project/agent-security-gate-x402/)
[![Glama.ai](https://img.shields.io/badge/Glama.ai-Approved-00ffcc?style=for-the-badge&logo=anthropic&logoColor=black)](https://glama.ai/mcp/servers/nohosa001-pixel/agent-security-gate-x402)
[![Cloud Run](https://img.shields.io/badge/Google_Cloud_Run-Live_24%2F7-4285F4?style=for-the-badge&logo=googlecloud&logoColor=white)](https://agent-security-gate-x402-7qxtp3324q-du.a.run.app/)
[![Polygon Network](https://img.shields.io/badge/Polygon_USDC-x402_Settlement-8247E5?style=for-the-badge&logo=polygon&logoColor=white)](https://polygon.technology)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-green.svg)](https://fastapi.tiangolo.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **Ultra-low latency (<10ms) deterministic security, prompt injection, secret key leak, dangerous AST code, and factual hallucination inspection micro-oracle with EIP-191 & EIP-712 cryptographic attestations on Polygon, Base, and Arbitrum.**

---

## 🖥️ Interactive Web Dashboard & Simulator (Live)

🌐 **[https://agent-security-gate-x402-7qxtp3324q-du.a.run.app/](https://agent-security-gate-x402-7qxtp3324q-du.a.run.app/)**

Explore the full consumer and enterprise visual interface directly in your browser:
- 🛡️ **Prompt Injection & Jailbreak Radar**: Live testing against DAN prompts, system tag escapes, and adversarial suffixes.
- ⚡ **Dangerous AST Code Analyzer**: Sub-millisecond Python syntax parsing detecting `os.system`, `subprocess`, `eval`, `exec`, and malicious sockets.
- 🔍 **Hallucination & NLI Fact-Checker**: Contrast agent generation with ground truth context to surface fabricated numbers and unanchored claims.
- 📜 **EIP-712 On-Chain Attestation & Calldata**: Instant generation of `v, r, s` ABI calldata for EVM smart contracts.
- 📡 **Real-Time Security Event Stream**: Live WebSocket event feed of inspection audits.

---

## 🔗 Live Service Links & Resources

| Service / Endpoint | Description | URL Link |
|---|---|---|
| 🖥️ **Web Dashboard** | Interactive visual UI, security simulator & audit tester | [Launch Dashboard](https://agent-security-gate-x402-7qxtp3324q-du.a.run.app/dashboard) |
| ⚡ **API Playground** | Browser-based interactive query sandbox | [Open Playground](https://agent-security-gate-x402-7qxtp3324q-du.a.run.app/playground) |
| 🛡️ **Live Inspection** | Core deterministic security & NLI hallucination check | [`/inspect`](https://agent-security-gate-x402-7qxtp3324q-du.a.run.app/inspect) |
| 📜 **On-Chain Calldata** | EIP-712 smart contract attestation calldata endpoint | [`/api/v1/gate/attestation/onchain`](https://agent-security-gate-x402-7qxtp3324q-du.a.run.app/api/v1/gate/attestation/onchain) |
| 📖 **Swagger API Docs** | Full interactive OpenAPI documentation | [View Swagger Docs](https://agent-security-gate-x402-7qxtp3324q-du.a.run.app/docs) |
| 🤖 **LLM Agent Manifest** | Machine-readable tool specifications | [`/llms.txt`](https://agent-security-gate-x402-7qxtp3324q-du.a.run.app/llms.txt) |

---

## ⚡ 1-Click MCP Integration (Claude Desktop & Cursor)

Connect to Claude Desktop, Cursor, Gemini, or any Model Context Protocol client instantly:

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

## 💎 Core Services & Capabilities

### 1. Ultra-Low Latency Prompt & Security Radar (<5ms)
Deterministic pattern and AST scanning neutralizing prompt injections, system tag breakouts (`</system_instruction>`), and API token / private key leakages before downstream agent propagation.

### 2. Python Code AST Hazard Auditing
In-memory Python Abstract Syntax Tree (AST) inspection isolating hazardous invocations:
- System execution (`os.system`, `os.popen`, `subprocess.Popen`, `subprocess.run`)
- Arbitrary code evaluation (`eval`, `exec`, `__import__`)
- Network socket reverse shells and unencrypted exfiltration vectors.

### 3. Factual Grounding & NLI Hallucination Verification
Compares LLM text claims against trusted source documents or ledger ground truths, outputting:
- Grounding ratio (0.0 to 1.0)
- Explicit list of fabricated numbers and ungrounded entities.

### 4. Cryptographic Proof-of-Safety & Smart Contracts
- **EIP-191 Signatures**: Off-chain attestation receipts for agent-to-agent validation.
- **EIP-712 Typed Data & Solidity Calldata**: Native integration with [`SecurityGateConsumer.sol`](contracts/SecurityGateConsumer.sol) on Polygon (137), Base (8453), and Arbitrum (42161).

---

## 📦 Quick Start & Installation

### Option 1. Run Instantly with `uvx` (No Installation Required)

```bash
# Run stdio MCP server directly for LLM clients
uvx agent-security-gate-x402
```

### Option 2. Install from PyPI

```bash
pip install agent-security-gate-x402

# Run MCP server (stdio mode)
agent-security-gate

# Or launch interactive terminal tester
python test_interactive.py
```

### Option 3. Local Development Server

```bash
git clone https://github.com/nohosa001-pixel/security-gate-x402.git
cd security-gate-x402
pip install -e .
uvicorn app.main:app --port 8000 --reload
```

---

## 📜 Smart Contract Integration (`SecurityGateConsumer.sol`)

Autonomous on-chain agents can verify security attestations directly in Solidity:

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./contracts/SecurityGateConsumer.sol";

contract AutonomousAgentExecutor {
    SecurityGateConsumer public immutable securityGate;

    constructor(address _securityGateAddress) {
        securityGate = SecurityGateConsumer(_securityGateAddress);
    }

    function executeGuardedAction(
        bytes32 payloadHash,
        uint8 riskScore,
        string calldata verdict,
        uint256 expiresAt,
        uint8 v,
        bytes32 r,
        bytes32 s,
        address target,
        bytes calldata callData
    ) external {
        // Enforces max 10% risk score threshold and valid oracle signature
        securityGate.verifyAndExecute(
            payloadHash,
            riskScore,
            verdict,
            expiresAt,
            v,
            r,
            s,
            target,
            callData,
            10 // maxRiskScore
        );
    }
}
```

---

## 🧪 Testing

Run the full pytest suite:

```bash
pytest -v tests/
```

Launch the interactive terminal tester:

```bash
python test_interactive.py
```

---

## 📄 License

MIT License &copy; 2026 Security Gate Team
