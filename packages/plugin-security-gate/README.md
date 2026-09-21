# 🛡️ @elizaos/plugin-security-gate

Deterministic local prompt injection defense, dangerous code pattern detection, and autonomous agent safety guardrails for ElizaOS.

---

## 🌟 Features

- 🔒 **100% Local-First by Default**: Runs entirely within the local node/bun process with **zero external network requests and zero data exfiltration**.
- ⚡ **Sub-Millisecond Deterministic Latency**: Instant regex pattern matching, heuristic command detection, and Unicode normalization (<1ms) for prompts, tool calls, and model inputs.
- 🛑 **Fail-Closed Safety**: High-risk injection payloads and dangerous commands are immediately blocked from executing.
- 🛡️ **Comprehensive Threat Interception**:
  - Adversarial prompt injections (instruction overrides, system prompt spoofing).
  - Jailbreak personas (DAN mode, Developer Mode overrides).
  - Obfuscation evasions (Zero-width characters `\u200B`, null-bytes `\0`).
  - Dangerous code execution patterns (`os.system`, `subprocess`, dynamic `eval`, `rm -rf`).
  - Accidental credential disclosures (private keys, raw hex seed material).
- 🌐 **Optional Opt-In Remote Oracle**: Connect to custom micro-oracle endpoints by explicitly setting `SECURITY_GATE_URL` (enforces 3s timeout and graceful fallback).

---

## 📦 Installation & Configuration

### 1. Add to Character JSON

```json
{
  "name": "SecureAgent",
  "plugins": ["@elizaos/plugin-security-gate"]
}
```

By default, the plugin runs in **Local Deterministic Mode** with no external network access.

### 2. (Optional) Configure Remote Micro-Oracle Verification

If you wish to route safety checks through an external micro-oracle:

```json
{
  "name": "SecureAgent",
  "plugins": ["@elizaos/plugin-security-gate"],
  "settings": {
    "secrets": {
      "SECURITY_GATE_URL": "https://your-security-gate-oracle.example.com",
      "SECURITY_GATE_API_KEY": "your-optional-api-key"
    }
  }
}
```

---

## 🧱 Components Included

- **`securityGatePreHandler` (ChatPreHandler)**: Fail-closed inbound guard that intercepts and analyzes inbound messages in sub-millisecond (<1ms) time before LLM inference or action dispatch, short-circuiting adversarial turns immediately.
- **`SECURITY_GATE_EVALUATOR`**: Evaluates conversational turns for prompt injections, jailbreaks, or policy violations and logs audit records into agent memory via standard Evaluator processors.
- **`INSPECT_SAFETY` Action**: Explicitly audits code snippets, transaction calldata, or dynamic instructions before critical tool execution (auto-detecting code snippets or accepting explicit `isCode` options). Delivers strictly typed `Content` and `ContentValue` callbacks.
- **`securityStatusProvider`**: Injects active security gate defense status and threat telemetry into the agent's context memory.

---

## 💻 Action Callback Contract (`ContentValue`)

When calling `INSPECT_SAFETY`, the action callback emits structured telemetry adhering to ElizaOS core typing:

```typescript
import { inspectSafetyAction } from "@elizaos/plugin-security-gate";

const result = await inspectSafetyAction.handler(
  runtime,
  message,
  state,
  {},
  async (callbackContent) => {
    // callbackContent conforms to Content
    console.log(callbackContent.text);
    // callbackContent.data conforms to Record<string, ContentValue>
    const { verdict, riskScore, threats, executionTimeMs, oracle, isCode } = callbackContent.data as {
      verdict: "ALLOW" | "WARN" | "BLOCK";
      riskScore: number;
      threats: string[];
      executionTimeMs: number;
      oracle?: boolean;
      isCode?: boolean;
    };
  }
);
```

---

## 🧪 Testing

```bash
bun test plugins/plugin-security-gate
# or
bunx vitest run
```

Comprehensive unit tests cover prompt injection blocking, zero-width character evasion normalization, dangerous command pattern detection, safe pass-through, and local fail-safe handling.

---

## 🌐 Multi-Chain Verified Smart Contracts

Security Gate x402 is live and verified across major EVM production networks. You can easily query verified contract addresses using the built-in helper:

```typescript
import { getSecurityGateContracts } from "@elizaos/plugin-security-gate";

// Retrieve verified addresses for Arbitrum One (Chain ID 42161)
const arb = getSecurityGateContracts(42161);
console.log("Safe Guard:", arb.contracts.safeSecurityGateGuard);
console.log("Escrow:", arb.contracts.agentEscrow);
console.log("Native USDC:", arb.tokens.usdc);
```

### Verified Mainnet Deployments

| Contract | Polygon Mainnet (137) | Base Mainnet (8453) | Arbitrum One (42161) |
| :--- | :--- | :--- | :--- |
| **SafeSecurityGateGuard** | [`0x5cC5...f173`](https://polygonscan.com/address/0x5cC5Afa2a97599d492A3E408Fdd95fD0b520f173#code) | [`0x306e...F408`](https://basescan.org/address/0x306e69E59E5bCEa769C6CeA76A79AFA8f2A5F408#code) | [`0x306e...F408`](https://arbiscan.io/address/0x306e69E59E5bCEa769C6CeA76A79AFA8f2A5F408#code) |
| **AgentCreditOracle** | [`0x6418...aB93`](https://polygonscan.com/address/0x6418f408cFf03F862D7691f01fAb00a895E6aB93#code) | [`0x227e...be93`](https://basescan.org/address/0x227e1129Ba9B39a50fb9E0802bA13A7F77Debe93#code) | [`0x227e...be93`](https://arbiscan.io/address/0x227e1129Ba9B39a50fb9E0802bA13A7F77Debe93#code) |
| **AgentComplianceRegistry** | [`0x2829...76DD`](https://polygonscan.com/address/0x28292D76E07E5539F15F3b97935dE8E0432E76DD#code) | [`0x821d...292D`](https://basescan.org/address/0x821d88Df97F6063a32fDff85FBad9784B9B7292D#code) | [`0x821d...292D`](https://arbiscan.io/address/0x821d88Df97F6063a32fDff85FBad9784B9B7292D#code) |
| **AgentEscrow** | [`0x8ACa...389d`](https://polygonscan.com/address/0x8ACafCEce0B1BFE140e75614b90FD1307b6f389d#code) | [`0x99FE...d278`](https://basescan.org/address/0x99FEd65Cf2D5378182c3481B300124BB1a8Ad278#code) | [`0x99FE...d278`](https://arbiscan.io/address/0x99FEd65Cf2D5378182c3481B300124BB1a8Ad278#code) |
| **AgentInsurancePool** | [`0xE67F...69C6`](https://polygonscan.com/address/0xE67F4BC75B11dBb3ef2C9Ad1848B4b193c2c69C6#code) | [`0x9030...3Ef2`](https://basescan.org/address/0x90308AedEe6430D11e5214cf9d2F563333D33Ef2#code) | [`0x9030...3Ef2`](https://arbiscan.io/address/0x90308AedEe6430D11e5214cf9d2F563333D33Ef2#code) |
| **AgentLendingPool** | [`0xe43a...82cF`](https://polygonscan.com/address/0xe43a9C368808B2dfF139D27789C40A3C8F2282cF#code) | [`0x5cC5...f173`](https://basescan.org/address/0x5cC5Afa2a97599d492A3E408Fdd95fD0b520f173#code) | [`0x5cC5...f173`](https://arbiscan.io/address/0x5cC5Afa2a97599d492A3E408Fdd95fD0b520f173#code) |
| **AgentFactoringPool** | [`0xd0Aa...5BB0`](https://polygonscan.com/address/0xd0Aa4Aed2AeDE14611B53C3e93CF784F3Fe05BB0#code) | [`0x6418...aB93`](https://basescan.org/address/0x6418f408cFf03F862D7691f01fAb00a895E6aB93#code) | [`0x6418...aB93`](https://arbiscan.io/address/0x6418f408cFf03F862D7691f01fAb00a895E6aB93#code) |
| **AgentTreasuryVault** | [`0xfCf3...C638`](https://polygonscan.com/address/0xfCf3BF5fB5858db9aE81bE458B39b0032fc0C638#code) | [`0xF8e1...ae55`](https://basescan.org/address/0xF8e1439F61c9F2d5FdbA382D524FabB35e12ae55#code) | [`0xF8e1...ae55`](https://arbiscan.io/address/0xF8e1439F61c9F2d5FdbA382D524FabB35e12ae55#code) |
| **SecurityGateConsumer** | [`0x9E3d...1DDA`](https://polygonscan.com/address/0x9E3dEE18D8139E1d20f9f7D1F6673c75727F1DDA#code) | [`0xdC6C...aB35`](https://basescan.org/address/0xdC6Cb774d51681Fcbba0E67Ca677dEc5705aaB35#code) | [`0xdC6C...aB35`](https://arbiscan.io/address/0xdC6Cb774d51681Fcbba0E67Ca677dEc5705aaB35#code) |

---

## 📚 Documentation & Specifications

- [🧙‍♂️ Ethereum Magicians ERC Proposal: IAgentTransactionGuard](https://ethereum-magicians.org/t/erc-ai-agent-proof-of-safety-attestation-transaction-guard-standard-iagenttransactionguard/29658)

---

## 📄 License

MIT
