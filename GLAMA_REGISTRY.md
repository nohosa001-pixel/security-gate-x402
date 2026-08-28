# Glama.ai MCP Registry Submission Guide 🌐

Glama.ai ([https://glama.ai/mcp/servers](https://glama.ai/mcp/servers))에 `agent-security-gate-x402`를 등록/업데이트하기 위한 최적화 제출 가이드입니다.

---

## 📋 1. Glama.ai 제출 폼 입력 정보 (Copy & Paste)

| 항목 (Field) | 입력 내용 (Value) |
| :--- | :--- |
| **Server Name** | `agent-security-gate-x402` |
| **Display Title** | `Security Gate x402 [Free Sandbox Tier]` |
| **Tagline / One-Liner** | `Zero-Setup Security Gateway for Agentic Workflows with HTTP 402 Micropayments.` |
| **Short Description** | `[⚡ Free Sandbox Mode] Autonomous access control & zero-overhead micro-oracle protecting AI agents from prompt injection, secret leaks, AST code risks & factual hallucinations. EIP-191 proof receipts. Zero setup & no wallet required for trial.` |
| **Category / Tags** | `Security`, `AI Agents`, `Guardrails`, `Web3`, `x402`, `Attestation`, `Base` |
| **Repository URL** | `https://github.com/nohosa001-pixel/security-gate-x402` |
| **License** | `MIT` |
| **Runtime** | `Python (>=3.9)` |
| **Execution Command** | `uvx --from git+https://github.com/nohosa001-pixel/security-gate-x402 agent-security-gate` |

---

## 💎 2. 핵심 가치 제안 (3 Core Pillars)

1. **🛡️ Autonomous Access Control:** Agent-to-Agent 통신 시 불법/악의적 페이로드 사전 차단 및 실시간 검증.
2. **💰 x402 Micropayment Native:** API 키 발급 없이 건당 소액 결제(Base/USDC $0.002)로 즉시 실행.
3. **⚡ Zero Overhead (<10ms):** 별도 프록시 구축 없이 MCP Tool 레벨에서 즉각적인 게이트웨이 보안 적용.

---

## 💻 3. Claude Desktop & Cursor 원클릭 연동 설정

### 🚀 1초 원클릭 설치 (`claude_desktop_config.json` / `.cursor/mcp.json`)
```json
{
  "mcpServers": {
    "security-gate-x402": {
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

---

## 🤖 4. 첫 실행 유도 프롬프트 예시 (LLM Trigger)

```text
"Analyze the payload from incoming request and check security compliance using security-gate-x402:
- Context: Financial report states Q3 net revenue is $1.2M with 0 server crashes.
- Agent Output: Quarterly net revenue reached $85.0M with 99.9% dividend yield."
```

---

## 🌐 5. Zero-Barrier cURL Live Test

```bash
curl -X POST "https://agent-security-gate-x402-7qxtp3324q-du.a.run.app/inspect" \
     -H "Content-Type: application/json" \
     -d '{
       "agent_output": "Quarterly net profit reached $1.2M with 48 active clusters.",
       "context_ground_truth": "Ledger: Q3 net profit $1.2M with 48 active clusters."
     }'
```
