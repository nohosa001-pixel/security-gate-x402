# Agent Output Security & Hallucination Gate (x402) 🛡️⚡

A deterministic, ultra-low latency (<10ms) security and hallucination inspection micro-oracle for autonomous AI agents.

- **Service Name:** `agent-security-gate-x402`
- **Settlement Rail:** HTTP 402 + [x402](https://x402.org) Protocol on **Base** network ($0.002 USDC per request)
- **Supported Standards:** Google AP2 (`/.well-known/ap2`), FastMCP, OpenAPI (`/docs`)
- **Compliance & Legal:** Zero-Data-Retention Policy (`/privacy`), Terms of Service & AS-IS Disclaimer (`/terms`), OFAC Sanctions Screening.
- **Deployment:** Google Cloud Platform (GCP Cloud Run / Cloud Build)

---

## 🚀 Key Features

1. **Prompt Injection & Role Hijacking Guard**
   - High-speed heuristic detection of instruction override directives, DAN modes, synthetic system tags, and zero-width character evasion.
2. **Secret & Key Leak Scanner**
   - Instant scanning for EVM 32-byte private keys, OpenAI / Anthropic API keys, GitHub PATs, AWS access keys, and asymmetric private key blocks.
3. **AST Dangerous Code Execution Guard**
   - Python AST analyzer blocking prohibited module imports (`os`, `subprocess`, `sys`, `socket`, `shutil`, `pty`, `ctypes`) and dangerous builtins (`eval`, `exec`, `__import__`).
4. **Numerical & Entity Hallucination Validator (Lightweight NLI)**
   - Cross-checks numerical claims and named entities in agent outputs against ground truth contexts, pinpointing fabricated numbers and ungrounded entities without heavy external LLM latency.
5. **OFAC & Mixer Sanctions Screening**
   - Automatically blocks requests from OFAC-sanctioned mixer contracts (e.g. Tornado Cash) and malicious addresses (403 Forbidden).
6. **Cryptographic Proof-of-Safety Attestation (EIP-191)**
   - Generates tamper-proof audit certificates signed by the gate issuer. Downstream orchestrators and smart contracts can verify proof of inspection before releasing task bounties or executing transactions.
7. **Autonomous Agent Self-Discovery (`llms.txt` & Google AP2)**
   - Exposes machine-readable discovery interfaces (`llms.txt`, `/.well-known/ap2.json`, `mcp_tool_spec.json`) allowing autonomous AI crawlers to discover, bind tools, and settle autonomously without human sign-up.
8. **Zero-Retention & Legal Disclaimers (`/terms`, `/privacy`)**
   - Formal in-memory processing policy (no customer data storage) and limitation of liability ($0.002 fee cap).
9. **One-Click Python SDK & `@gate_inspect` Decorator**
   - Seamless integration with built-in `verify_attestation()` for LangChain, CrewAI, AutoGen, or custom agent pipelines.

---

## 📁 Project Structure

```text
agent-security-gate-x402/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI server, /terms, /privacy, & x402 payment enforcement
│   ├── security_engine.py   # Injection, key leak, AST & NLI verification logic
│   ├── x402_verifier.py     # x402 facilitator signature & OFAC verification
│   └── schemas.py           # Pydantic request/response schemas
├── sdk/
│   ├── __init__.py
│   └── agent_gate_sdk.py    # Python SDK client & @gate_inspect decorator
├── tests/
│   ├── __init__.py
│   └── test_client.py       # End-to-end payment, security, & SDK test suite
├── .well-known/
│   └── ap2.json             # Google AP2 manifest
├── mcp_tool_spec.json       # MCP tool definition for Claude/Cursor/LLMs
├── cloudbuild.yaml          # GCP Cloud Build automated pipeline
├── deploy-gcp.sh            # GCP Cloud Run deployment script (Bash)
├── deploy-gcp.ps1           # GCP Cloud Run deployment script (PowerShell)
├── Dockerfile               # Ultra-lightweight container
├── requirements.txt         # Dependencies
├── .env.example             # Environment template
└── README.md
```

---

## 🐍 Python SDK & Decorator Usage

Install the client SDK in your agent project and wrap your LLM calls:

```python
from sdk.agent_gate_sdk import SecurityGateClient, gate_inspect

client = SecurityGateClient(
    gate_url="https://your-gate-service-url.run.app",
    private_key="0xYourAgentEVMKey..."
)

# 1. Direct Inspection
result = client.inspect(
    agent_output="The total quarterly net revenue was $1.2M.",
    context_ground_truth="Quarterly revenue: $1.2M."
)
print(result["audit"]["verdict"])  # "PASSED"

# 2. Function Decorator Middleware
@gate_inspect(client=client, strict=True)
def run_agent_reasoning(task_prompt: str) -> str:
    # Your LLM call (OpenAI, Anthropic, LangChain, etc.)
    return llm.invoke(task_prompt)
```

---

## ☁️ Google Cloud Platform (GCP Cloud Run) Deployment

### Prerequisites

1. Install [Google Cloud SDK (`gcloud`)](https://cloud.google.com/sdk/docs/install).
2. Authenticate: `gcloud auth login` and `gcloud config set project <YOUR_GCP_PROJECT_ID>`.

### One-Click Deployment

#### Linux / macOS

```bash
chmod +x deploy-gcp.sh
./deploy-gcp.sh
```

#### Windows (PowerShell)

```powershell
.\deploy-gcp.ps1
```

Once deployed, your Cloud Run service URL will be printed (e.g. `https://agent-security-gate-x402-xxx.a.run.app`).

---

## 🛠️ Local Development & Testing

```bash
# 1. Start local server
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload

# 2. Run test suite
python tests/test_client.py
# or
pytest tests/test_client.py -v
```
