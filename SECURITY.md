# Security Policy 🛡️

The Sheriff of Agent Finance (`agent-security-gate-x402`) provides deterministic security evaluation, prompt injection defense, malicious AST code detection, and cryptographic on-chain attestations for autonomous agent transactions and wallets.

We take the safety of autonomous agent financial operations and off-chain/on-chain integrations seriously.

---

## 🔒 Supported Versions

Only the latest active versions receive continuous security updates and deterministic threat rule patches.

| Version | Supported | Security Rule Feed |
| --- | --- | --- |
| >= 0.1.0 | :white_check_mark: | Active (Live & Auto-updated) |
| < 0.1.0 | :x: | Deprecated |

---

## 🚨 Reporting a Vulnerability

If you discover a security vulnerability, prompt injection bypass, or smart contract logic flaw, please **do not open a public GitHub issue**.

### Reporting Channels

1. **GitHub Private Vulnerability Reporting**:
   Use the [Report a vulnerability](https://github.com/nohosa001-pixel/security-gate-x402/security/advisories/new) feature directly within our GitHub repository.
2. **Email Disclosure**:
   Send details to `security@agent-finance.org` or contact the repository owner privately via GitHub.

### What to Include

- A clear description of the vulnerability, attack vector, or bypass scenario.
- Minimal reproducible sample code, payload, or transaction hash.
- Potential impact on autonomous agents or on-chain settlement.
- Your contact details for attribution and coordination.

### Response Time & SLA

- **Initial Acknowledgment**: Within 24 hours.
- **Triage & Severity Assessment**: Within 48 hours.
- **Remediation & Patch Deployment**: Critical vulnerabilities are patched on the live micro-oracle within 24–72 hours.

---

## 🏛️ Threat Model & Architectural Guarantees

The Sheriff architecture enforces a defense-in-depth security model across five distinct layers:

```text
┌─────────────────────────────────────────────────────────────┐
│                      Autonomous Agent                       │
└──────────────────────────────┬──────────────────────────────┘
                               │
            ┌──────────────────┴──────────────────┐
            ▼                                     ▼
┌───────────────────────┐             ┌───────────────────────┐
│   Off-Chain Oracle    │             │  Client-Side Wallet   │
│ 1. Prompt Injection   │             │ 4. BoundedAgentWallet │
│ 2. Python AST Sandbox │             │    - Per-tx cap       │
│ 3. NLI Hallucination  │             │    - Daily ceiling    │
└───────────┬───────────┘             │    - Whitelisting     │
            │                         └───────────┬───────────┘
            ▼                                     ▼
┌─────────────────────────────────────────────────────────────┐
│              EIP-712 / EIP-191 Signed Attestation           │
│              ZERO_LIABILITY_AS_IS_PROVENANCE_V1             │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│            On-Chain Execution Barrier (Polygon 137)         │
│     SecurityGateConsumer.sol / SafeSecurityGateGuard.sol    │
└─────────────────────────────────────────────────────────────┘
```

### 1. Deterministic Prompt Injection & Escape Neutralization (<5ms)

- Evaluates inbound inputs against known adversarial evasion vectors, DAN prompts, and delimiter manipulation (e.g. `</system_instruction>`, `<script>`).
- Completely deterministic regex and token scanning without stochastic LLM latency or model blindspots.

### 2. Python AST Code Hazard Sandbox

- Uses Python's native Abstract Syntax Tree (`ast.parse`) in an isolated analyzer.
- Flags and halts execution of critical system functions:
  - System commands: `os.system`, `os.popen`, `subprocess.Popen`, `subprocess.run`
  - Dynamic evaluation: `eval`, `exec`, `__import__`
  - Network exploitation: Unauthorized raw socket binding and reverse shells.

### 3. Factual Grounding & Hallucination Guard

- Matches LLM-generated assertions against provided grounding documents or immutable ledger entries.
- Flags unanchored numerical figures, false addresses, or hallucinated parameter quantities before funds are dispatched.

### 4. Client-Side Bounded-Wallet Guardrails (`BoundedAgentWallet`)

- Enforces hard financial guardrails in client runtime memory and on-disk persistent state:
  - **Per-Transaction Spend Cap**: Guaranteed hard limit per API call (default $0.05 USDC).
  - **24-Hour Cumulative Spend Ceiling**: Hard daily stop (default $1.00 USDC).
  - **Verified Recipient Whitelisting**: Guarantees funds can only be sent to authorized gate treasuries.
  - **Replay Protection**: Nonce verification and ledger timestamp checks.

### 5. Cryptographic Attestations & Zero-Liability Provenance

- All inspection evaluations issue an **EIP-191** or **EIP-712** signature verifiable on-chain:
  - Payload SHA-256 fingerprint binding.
  - Risk score (0–100) and explicit verdict (`ALLOW`, `WARN`, `BLOCK`).
  - Legal disclaimer binding: [`ZERO_LIABILITY_AS_IS_PROVENANCE_V1`](TERMS_OF_SERVICE.md).
  - Programmatic verification via `GET /api/v1/terms` or header `X-Sheriff-Terms-Url`.
  - Enforces strict liability cap ($50 USD / 30-day fee ceiling) and explicit non-financial advice classification.

---

## ⛓️ On-Chain Contract Security

Official smart contracts are deployed on **Polygon Mainnet (Chain ID 137)**:

- **`SecurityGateConsumer`**: `0x9E3dEE18D8139E1d20f9f7D1F6673c75727F1DDA`
- **`SafeSecurityGateGuard`**: `0x5cC5Afa2a97599d492A3E408Fdd95fD0b520f173`

These contracts verify oracle signatures, risk thresholds, and payload commitments before allowing autonomous transactions to execute.
