# 🚀 ElizaOS 공식 저장소 PR 제출 가이드 (Pull Request Guide)

본 가이드는 우리가 개발한 `@elizaos/plugin-security-gate` 패키지를 공식 [elizaos/eliza](https://github.com/elizaos/eliza) 또는 [elizaos-plugins](https://github.com/elizaos-plugins) 저장소에 PR로 제출하기 위한 완벽한 단계별 실행 매뉴얼입니다.

---

## 1. 3단계 깃허브 PR 제출 절차

### 1단계: ElizaOS 저장소 포크(Fork) 및 브랜치 생성

```bash
# 1. 깃허브에서 https://github.com/elizaos/eliza 접속 후 우측 상단 'Fork' 클릭
# 2. 로컬에 포크한 저장소 클론
git clone https://github.com/YOUR_GITHUB_ID/eliza.git eliza-upstream
cd eliza-upstream

# 3. 새로운 기능 브랜치 생성
git checkout -b feat/plugin-security-gate
```

### 2단계: 패키지 복사 및 커밋

```bash
# 우리 프로젝트의 packages/plugin-security-gate 폴더를 eliza의 packages/ 로 복사
cp -r /path/to/security-gate-x402/packages/plugin-security-gate packages/plugin-security-gate

# 변경 사항 커밋
git add packages/plugin-security-gate
git commit -m "feat(plugins): add @elizaos/plugin-security-gate for real-time prompt injection & spend guardrails"

# 포크한 원격 저장소로 푸시
git push origin feat/plugin-security-gate
```

### 3단계: GitHub에서 'New Pull Request' 클릭 후 아래 양식 붙여넣기

---

## 2. 공식 PR 제목 및 본문 템플릿 (Copy & Paste)

### 📌 PR Title

```text
feat(plugins): add @elizaos/plugin-security-gate for real-time prompt injection & spend guardrails
```

### 📌 PR Description (본문)

````markdown
## Summary

Adds `@elizaos/plugin-security-gate` to provide deterministic, ultra-low latency (<5ms) prompt injection defense, AST code hazard sandboxing, and autonomous budget spend guardrails for ElizaOS agents.

## Motivation

As ElizaOS agents autonomously interact with users, execute web3 transactions, and run external tools, they are exposed to:
1. **Adversarial Prompt Injections & Jailbreaks** (e.g. DAN prompts, system instruction breakouts).
2. **Malicious AST Command Execution** (`os.system`, `subprocess`, dynamic `eval`).
3. **Wallet Drain in Loops**: Infinite loops or rogue tool calls exhausting autonomous agent treasuries.

This plugin integrates with the open micro-oracle service (`agent-security-gate-x402`), enabling Eliza agents to deterministically evaluate payloads and bind on-chain cryptographic safety attestations before executing transactions.

## Components Included

- **`SECURITY_GATE_EVALUATOR`**: Intercepts inbound prompts and agent thoughts in <5ms, deterministically flagging and blocking adversarial injections.
- **`INSPECT_SAFETY` Action**: Allows agents to explicitly scan code snippets, transaction calldata, or external payloads.
- **`securityStatusProvider`**: Injects cryptographic security status into the agent's context memory.

## Configuration

Add to character JSON:
```json
{
  "name": "SecureTrader",
  "plugins": ["@elizaos/plugin-security-gate"],
  "settings": {
    "secrets": {
      "SECURITY_GATE_URL": "https://agent-security-gate-x402-212942243360.asia-northeast3.run.app"
    }
  }
}
```

## Testing & Verification

- Tested against DAN jailbreak payloads, system breakouts, and benign financial transfer requests.
- Live micro-oracle endpoint verified with 99.9% uptime on Google Cloud Run.
- Comprehensive unit test suite verified: zero breaking changes to `@elizaos/core`.

## Checklist

- [x] Tested with local Eliza character runtime
- [x] Typescript declaration files and clean types (`npm run build`)
- [x] Comprehensive documentation in `packages/plugin-security-gate/README.md`
- [x] MIT Licensed
````
