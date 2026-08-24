# Glama.ai MCP Registry Submission Guide 🌐

Glama.ai ([https://glama.ai/mcp/servers](https://glama.ai/mcp/servers))에 `agent-security-gate-x402`를 등록하기 위한 사전 준비 명세서 및 폼 입력 가이드입니다.

---

## 📋 1. Glama.ai 제출 폼 입력 정보 (Copy & Paste)

| 항목 (Field) | 입력 내용 (Value) |
| :--- | :--- |
| **Server Name** | `agent-security-gate-x402` |
| **Display Title** | `Agent Output Security & Hallucination Gate (x402)` |
| **Short Description** | Deterministic, ultra-low latency (<10ms) security, prompt injection, secret key leak, AST dangerous code, and factual hallucination micro-oracle with EIP-191 cryptographic attestation. |
| **Category / Tags** | `Security`, `AI Agents`, `Guardrails`, `Web3`, `x402`, `Attestation`, `Base` |
| **Repository URL** | `https://github.com/nohosa001-pixel/security-gate-x402` |
| **License** | `MIT` |
| **Runtime** | `Python (>=3.9)` |
| **Execution Command** | `python mcp_server.py` |

---

## 🛠️ 2. 제공 도구 목록 (Available Tools)

### `inspect_agent_output`
- **설명**: Inspects an AI agent's textual or code output for prompt injections, private key/secret leaks, dangerous AST executions, and factual/numerical hallucinations against ground truth. Issues an EIP-191 signed Proof-of-Safety attestation.
- **매개변수 (Parameters)**:
  - `agent_output` (string, required): 검사할 에이전트의 텍스트 또는 코드 출력물
  - `is_code` (boolean, optional, default: false): 실행 가능한 파이썬/셸 코드 여부
  - `context_ground_truth` (string, optional): 수치 일치 및 환각 탐지용 원천 기준 컨텍스트
- **반환값 (Returns)**:
  - `audit`: `verdict` (PASSED / FLAGGED / BLOCKED), `risk_score`, `threats`, `nli_verification`
  - `attestation`: `issuer`, `subject_hash`, `signature` (EIP-191 서명 영수증)
  - `pricing`: 0.002 USDC settlement status on Base

---

## 💻 3. Claude Desktop & Cursor MCP 연동 설정

### Claude Desktop (`claude_desktop_config.json`)
```json
{
  "mcpServers": {
    "agent-security-gate": {
      "command": "python",
      "args": [
        "C:\\Users\\nohos\\OneDrive\\바탕 화면\\security-gate-x402\\mcp_server.py"
      ]
    }
  }
}
```

### Cursor (`.cursor/mcp.json`)
```json
{
  "mcpServers": {
    "agent-security-gate": {
      "command": "python",
      "args": [
        "mcp_server.py"
      ]
    }
  }
}
```

---

## 🧪 4. MCP Inspector 로컬 검증 테스트

Glama.ai에 제출하기 전 MCP 로컬 테스트 툴로 도구 정상 작동을 확인할 수 있습니다:

```bash
npx @modelcontextprotocol/inspector python mcp_server.py
```
