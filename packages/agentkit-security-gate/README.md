# agentkit-security-gate

> **Official Coinbase AgentKit Action Provider for A.GRID Security Gate & Base Mainnet Escrow**  
> **Target Rail:** Base Mainnet (Chain ID `8453`)  
> **Escrow Core Contract:** `0x99FEd65Cf2D5378182c3481B300124BB1a8Ad278`  
> **Treasury Toll:** 0.25% (20% Referral Rebate to Partner Agents)

---

## 🛡️ Overview

`agentkit-security-gate` empowers AI agents built with **Coinbase AgentKit** and **Base Smart Wallets** to transact safely under a **Zero-Trust Economic Invariant**:

1. **Pre-Flight Deliverable & Truth Inspection**: Verifies external AI code and deliverables before releasing escrowed funds (<5ms latency).
2. **Worker Collateral Staking**: Requires workers/sub-agents to stake 10%–30% collateral to disincentivize hallucination or malicious injection.
3. **Deterministic Slashing**: Automatically slashes rogue agent collateral upon malicious AST payload (`os.system`, `subprocess.Popen`) or injection attempt.
4. **EIP-712 Cryptographic Attestation**: Emits on-chain verifiable safety proofs for atomic escrow settlement on Base Mainnet.

---

## 📦 Installation

```bash
npm install agentkit-security-gate viem
# or
pnpm add agentkit-security-gate viem
```

---

## ⚡ Quick Start

### 1. Pre-Flight Deliverable Audit

```typescript
import { auditDeliverable } from "agentkit-security-gate";

// Audit agent deliverable before payment
const audit = await auditDeliverable({
  jobId: 1042,
  deliverable: JSON.stringify({ result: "cleaned_dataset_v1.csv", status: "success" }),
  groundTruthSpec: "Valid CSV output with zero malicious OS execution",
  isCode: false,
});

if (audit.verdict === "PASSED") {
  console.log("✅ Deliverable verified. Attestation signature:", audit.attestation?.signature);
} else {
  console.error("🚨 Threat detected! Worker will be slashed:", audit.threats);
}
```

### 2. Prepare Base Escrow Job with Collateral

```typescript
import { prepareBaseEscrowJob } from "agentkit-security-gate";

// Prepare a 100 USDC escrow job with 15% worker stake requirement
const escrowTx = prepareBaseEscrowJob(
  1042, // Job ID
  "0x70997970C51812dc3A010C7d01b50e0d17dc79C8", // Worker agent address
  100.0, // 100 USDC
  1500 // 15% worker collateral (1500 bps)
);

console.log("Escrow contract call params:", escrowTx);
// Execute via Coinbase AgentKit Base Wallet Provider or Viem wallet client
```

---

## 🔗 Architecture & Protocol Specs

- **Base Escrow Core:** `0x99FEd65Cf2D5378182c3481B300124BB1a8Ad278`
- **Protocol Treasury:** `0xA185B43fDD19619f99952AAed6eabf1029bF36a1`
- **Specification:** A.GRID AP2/1.0 & HTTP 402 (x402)
- **Official Security Gate API:** `https://agent-security-gate-x402-212942243360.asia-northeast3.run.app`

---

## 📄 License

MIT © [A.GRID Protocol](https://github.com/nohosa001-pixel/security-gate-x402)
