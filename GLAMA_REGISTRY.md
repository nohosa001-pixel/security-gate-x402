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
| **Category / Tags** | `Security`, `AI Agents`, `Guardrails`, `Web3`, `x402`, `Attestation`, `Polygon` |
| **Repository URL** | `https://github.com/nohosa001-pixel/security-gate-x402` |
| **License** | `MIT` |
| **Runtime** | `Python (>=3.9)` |
| **Execution Command** | `uvx --from git+https://github.com/nohosa001-pixel/security-gate-x402 agent-security-gate` |

---

## 💎 2. 핵심 가치 제안 (3 Core Pillars)

1. **🛡️ Autonomous Access Control:** Agent-to-Agent 통신 시 불법/악의적 페이로드 사전 차단 및 실시간 검증.
2. **💰 x402 Micropayment Native:** API 키 발급 없이 건당 소액 결제(Polygon/USDC $0.002)로 즉시 실행.
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

---

## 🏆 6. TDQS (Tool Definition & Quality Score) A-Grade Specifications

Glama.ai 평가 기준에 맞춘 6종 도구 구성 및 오호출 방지(Disambiguation) 가이드라인:

| Tool Name | Core Purpose | When to Use (Positive Guideline) | When NOT to Use (Negative Guideline) |
| :--- | :--- | :--- | :--- |
| `inspect_agent_output` | Comprehensive NLI Hallucination & Security Audit with EIP-191 Attestation | RAG 컨텍스트 대비 수치/사실 환각 검증 및 서명 영수증 발행 시 | 단순 초고속 사전 필터링 시에는 `verify_agent_output` 사용 |
| `verify_agent_output` | Ultra-fast (<5ms) Prompt Injection & Secret Leak Scanner | 프롬프트 인젝션, 탈옥, API 키/개인키 사전 스크리닝 시 | 사실 검증이나 암호학적 온체인 증명이 필요할 때는 `inspect_agent_output` 사용 |
| `inspect_code_ast_safety` | Deterministic Python AST parser for dangerous operations | 샌드박스 실행 전 Python 코드 위험 구문(subprocess, eval, socket) 정적 분석 시 | 일반 자연어 텍스트는 `verify_agent_output` 사용 |
| `get_onchain_security_attestation` | Polygon/Base EIP-712 Smart Contract Security Calldata (v, r, s) | Safe Vault 또는 온체인 스마트 컨트랙트 실행 전 가드레일 서명 생성 시 | 오프체인 텍스트 검증은 `inspect_agent_output` 사용 |
| `get_agent_credit_rating` | Dynamic FICO-style Credit Rating (300-850) & Lending Limit | 자율 에이전트 EVM 지갑 기준 신용 등급 및 무담보 대출 한도 조회 시 | 보안 감사나 코드 분석에는 사용 불가 |
| `get_eu_ai_act_compliance_passport` | EU AI Act (Regulation EU 2024/1689) Official Compliance Passport | EU AI법 제50조 및 제53조 투명성/기초 모델 규제 준수 여권 발급 시 | 런타임 보안 필터링에는 사용 불가 |

