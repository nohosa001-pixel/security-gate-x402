# Contributing to agent-security-gate-x402 🛡️

Thank you for your interest in contributing to **Agent Output Security & Hallucination Gate (x402)**!

## 🚀 Development Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/nohosa001-pixel/security-gate-x402.git
   cd security-gate-x402
   ```

2. **Create a virtual environment and install dependencies:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Or `.venv\Scripts\activate` on Windows
   pip install -r requirements.txt
   pip install pytest flake8
   ```

3. **Run local test suite:**
   ```bash
   pytest tests/test_client.py -v
   ```

4. **Verify MCP server with MCP Inspector:**
   ```bash
   npx @modelcontextprotocol/inspector python mcp_server.py
   ```

## 🛠️ Contribution Guidelines

- **Deterministic Security Heuristics:** Ensure all pattern matches and AST security rules remain ultra-low latency (<10ms).
- **Zero-Retention:** Do NOT add persistent logging or disk-storage of raw agent outputs or customer payloads.
- **Cryptographic Attestation:** Preserve EIP-191 attestation signature generation integrity.
- **Pull Requests:** Write clear commit messages and include tests for new threat vectors or NLI hallucination checks.

## 📄 License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
