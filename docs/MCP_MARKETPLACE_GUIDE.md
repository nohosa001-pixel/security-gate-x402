# 🔌 MCP (Model Context Protocol) Marketplace & Integration Guide
## Anthropic Claude Desktop, Cursor IDE, Glama.ai & Smithery.ai Setup

A.GRID `agent-security-gate-x402` exposes a high-performance **Model Context Protocol (MCP)** server (`mcp_server.py`), enabling AI models in **Anthropic Claude Desktop** and **Cursor IDE** to deterministically audit code, verify prompt injection defense, check M2M escrow deliverables, and query the Sovereign RWA Treasury.

---

### 1. 🤖 Cursor IDE Integration (Instant Setup)

Cursor natively supports workspace MCP servers via `.cursor/mcp.json`.

#### Option A: Workspace Auto-Discovery (Recommended)
This repository already includes [`.cursor/mcp.json`](file:///c:/Users/nohos/OneDrive/%EB%B0%94%ED%83%95%20%ED%99%94%EB%A9%B4/security-gate-x402/.cursor/mcp.json):
```json
{
  "mcpServers": {
    "security-gate-x402": {
      "command": "python",
      "args": ["-m", "mcp_server"],
      "env": {
        "PYTHONIOENCODING": "utf-8"
      }
    }
  }
}
```

#### Option B: Global Cursor Settings
1. Open Cursor Settings: `Ctrl + Shift + J` (Windows) or `Cmd + ,` (Mac).
2. Navigate to **Features** ➔ **MCP Servers** ➔ **Add New MCP Server**.
3. Fill in:
   - **Name**: `security-gate-x402`
   - **Type**: `command`
   - **Command**: `python -m mcp_server`

---

### 2. 🧠 Anthropic Claude Desktop Integration

Claude Desktop allows Claude 3.5 Sonnet and Claude 3.7 to invoke A.GRID tools directly during conversations.

#### Config File Location:
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`  
  *(Path: `C:\Users\<Username>\AppData\Roaming\Claude\claude_desktop_config.json`)*
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`

#### Configuration Snippet:
```json
{
  "mcpServers": {
    "security-gate-x402": {
      "command": "python",
      "args": [
        "c:/Users/nohos/OneDrive/바탕 화면/security-gate-x402/mcp_server.py"
      ],
      "env": {
        "PYTHONIOENCODING": "utf-8"
      }
    }
  }
}
```
*Restart Claude Desktop after saving the configuration. A hammer icon (🔨) will appear in the input box indicating active tools.*

---

### 3. 🌐 Glama.ai Marketplace (Approved Status)

A.GRID is officially verified and listed on **Glama.ai**, the premier public MCP registry for Anthropic ecosystems:

- **Registry Listing**: [https://glama.ai/mcp/servers/nohosa001-pixel/security-gate-x402](https://glama.ai/mcp/servers/nohosa001-pixel/security-gate-x402)
- **Status**: **Approved & Verified**

Developers can discover and install our server with 1 click directly from the Glama web catalog.

---

### 4. ⚡ Smithery.ai Marketplace (1-Line CLI Install)

Smithery is the global CLI package manager for MCP tools:

```bash
# Run directly via npx
npx -y @smithery/cli run agent-security-gate-x402 --client claude

# Or install globally for Cursor
npx -y @smithery/cli install agent-security-gate-x402 --client cursor
```

---

### 5. 🛠️ Available MCP Tools

Once connected, Claude or Cursor can execute the following actions:

| Tool Name | Description |
| :--- | :--- |
| `inspect_agent_output` | Deep NLI fact-checking and prompt injection defense with EIP-191 proof |
| `verify_agent_output` | Ultra-fast (<5ms) pre-flight secret leak and regex scanner |
| `inspect_code_ast_safety` | Deterministic Python AST scanner for `os.system`, `subprocess`, shell escapes |
| `get_onchain_security_attestation` | Generates EIP-712 `v, r, s` calldata for EVM smart contracts |
| `audit_agent_escrow_task` | Audits M2M task deliverables for on-chain capital release or slashing |
| `query_sovereign_treasury` | Inspects 100% US Treasury Bill reserves ($1.58M) and EIP-712 PoR |
