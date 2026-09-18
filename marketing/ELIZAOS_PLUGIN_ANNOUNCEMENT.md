# 📢 ElizaOS Official Plugin Announcement Kit

> **PR #31451 Approved**: `feat(plugins): add @elizaos/plugin-security-gate for real-time prompt injection & spend guardrails`

---

## 🐦 1. X (Twitter) Announcement Thread

### [Tweet 1: The Milestone Announcement]
🚨 BREAKING: `@elizaos/plugin-security-gate` has officially received reviewer APPROVAL for upstream inclusion in ElizaOS! (PR #31451)

Now every autonomous agent built on @elizaos can have deterministic, sub-millisecond prompt injection defense and financial guardrails with ZERO extra lines of code.

Here is why this changes everything for agent safety 🧵👇 (1/4)
#ElizaOS #ai16z #AIAgents #Web3Security #CyberSecurity

### [Tweet 2: The Core Guarantee - Zero LLM Waste]
⚡ How it works: Fail-Closed Inbound PreHandler (<0.5ms)

When an attacker tries DAN jailbreaks, system prompt exfiltration, or null-byte evasion:
🛑 Intercepted before the agent context memory.
💰 Incurred LLM API calls: ZERO (0)
💸 Incurred Token costs: $0.00
🛡️ Action side-effects: ZERO (0)

Your agent doesn't even waste 1 token listening to hackers. (2/4)

### [Tweet 3: Dead-Simple 1-Line Setup]
Just add `@elizaos/plugin-security-gate` to your `character.json`:

```json
{
  "name": "SecureTrader",
  "plugins": ["@elizaos/plugin-security-gate"]
}
```

100% local-first by default. No external network exfiltration. Optional opt-in to enterprise x402 micro-oracles with EIP-712 cryptographic proofs on Polygon/Base/Arbitrum. (3/4)

### [Tweet 4: Links & Try It Live]
🔗 Check out the PR & Benchmark:
• GitHub PR: https://github.com/elizaOS/eliza/pull/31451
• Core Repository: https://github.com/nohosa001-pixel/security-gate-x402
• Run live benchmark in 5 seconds:
  `node examples/live_showcase_security_gate.mjs`

Massive thanks to the @elizaos review team! Let's build secure autonomous agent swarms together. 🛡️🤖 (4/4)

---

## 💬 2. ElizaOS Official Discord Announcement (For `#plugins` or `#showcase`)

**Subject**: 🛡️ New Plugin: `@elizaos/plugin-security-gate` (PR #31451 Approved!)

Hey builders! 👋

Autonomous agents holding wallet keys or executing tools shouldn't be vulnerable to 1-shot prompt injections. We're excited to share that **`@elizaos/plugin-security-gate`** has been reviewed and approved in **PR #31451**!

### What does it do?
* **Sub-Millisecond PreHandler (<0.5ms)**: Blocks jailbreaks (DAN, Developer Mode), instruction overrides, and null-byte/zero-width evasion attempts *before* LLM generation.
* **Fail-Closed & Zero Token Waste**: When an attack turn is detected, the turn is short-circuited immediately—**0 model API calls, 0 token costs, 0 action side-effects**.
* **100% Local-First by Default**: Runs purely in-memory via regex AST rules. No data sent to third-party endpoints unless explicitly opted-in via `SECURITY_GATE_URL`.
* **Action & Evaluator Support**: Includes `INSPECT_SAFETY` action for tool parameters and `SECURITY_GATE_EVALUATOR` for audit memory logging.

### How to use:
```json
{
  "name": "MySecureAgent",
  "plugins": ["@elizaos/plugin-security-gate"]
}
```

👉 PR Link: https://github.com/elizaOS/eliza/pull/31451  
We'd love your feedback, stars, and ideas on further guardrails! 🚀
