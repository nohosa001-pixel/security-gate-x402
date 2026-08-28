# Glama.ai MCP Registry Submission Guide 🌐

Glama.ai ([https://glama.ai/mcp/servers](https://glama.ai/mcp/servers))에 `agent-security-gate-x402`를 등록/업데이트하기 위한 최적화 제출 가이드입니다.

---

## 📋 1. Glama.ai 제출 폼 입력 정보 (Copy & Paste)

| 항목 (Field) | 입력 내용 (Value) |
| :--- | :--- |
| **Server Name** | `agent-security-gate-x402` |
| **Display Title** | `Agent Output Security & Hallucination Gate [Free Tier]` |
| **Short Description** | `[⚡ Instant Free Trial] Ultra-low latency (<10ms) micro-oracle protecting AI agents from prompt injection, secret leaks, AST code risks & factual hallucinations. EIP-191 proof receipts. Zero setup & no wallet required for trial.` |
| **Category / Tags** | `Security`, `AI Agents`, `Guardrails`, `Web3`, `x402`, `Attestation`, `Base` |
| **Repository URL** | `https://github.com/nohosa001-pixel/security-gate-x402` |
| **License** | `MIT` |
| **Runtime** | `Python (>=3.9)` |
| **Execution Command** | `uvx --from git+https://github.com/nohosa001-pixel/security-gate-x402 agent-security-gate` |

---

## 🛠️ 2. 제공 도구 목록 (Available Tools)

### `inspect_agent_output`
- **설명**: Inspects an AI agent's textual or code output for prompt injections, private key/secret leaks, dangerous AST executions, and factual/numerical hallucinations against ground truth. Issues an EIP-191 signed Proof-of-Safety attestation. (Free tier enabled by default).
- **매개변수 (Parameters)**:
  - `agent_output` (string, required): 검사할 에이전트의 텍스트 또는 코드 출력물 (기본값 제공)
  - `is_code` (boolean, optional, default: false): 실행 가능한 파이썬/셸 코드 여부
  - `context_ground_truth` (string, optional): 수치 일치 및 환각 탐지용 원천 기준 컨텍스트
- **반환값 (Returns)**:
  - `audit`: `verdict` (PASSED / FLAGGED / BLOCKED), `risk_score`, `threats`, `nli_verification`
  - `attestation`: `issuer`, `subject_hash`, `signature` (EIP-191 암호학적 서명 영수증)
  - `pricing`: Free tier / $0.002 USDC settlement status on Base

---

## 💻 3. Claude Desktop & Cursor 원클릭 연동 설정

### 🚀 1초 원클릭 설치 (via `uvx` - 로컬 clone 필요 없음 / 가장 추천)
```json
{
  "mcpServers": {
    "security-gate": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/nohosa001-pixel/security-gate-x402",
        "agent-security-gate"
      ]
    }
  }
}
```

### 💻 로컬 Clone 수동 연동 (`claude_desktop_config.json` / `.cursor/mcp.json`)
```json
{
  "mcpServers": {
    "security-gate": {
      "command": "python",
      "args": [
        "mcp_server.py"
      ]
    }
  }
}
```

---

## 🌐 4. 터미널 즉시 테스트 (Zero Setup cURL)

로컬 설정 없이 즉시 클라우드 라이브 오라클을 무료로 테스트할 수 있습니다:

```bash
curl -X POST "https://agent-security-gate-x402-7qxtp3324q-du.a.run.app/inspect" \
     -H "Content-Type: application/json" \
     -d '{
       "agent_output": "Quarterly net profit reached $1.2M with 48 active clusters.",
       "context_ground_truth": "Ledger: Q3 net profit $1.2M with 48 active clusters."
     }'
```

---

## 🧪 5. MCP Inspector 로컬 검증 테스트

```bash
npx @modelcontextprotocol/inspector uvx --from git+https://github.com/nohosa001-pixel/security-gate-x402 agent-security-gate
```
