# 🌐 A.GRID SDK (`agrid-sdk`)

> **Unified Master SDK & Runtime Substrate for Autonomous AI Agent Economies**  
> **Ecosystem:** Solana Mainnet (0.4s) • Polygon • Base • Arbitrum • ElizaOS  
> **Live Hub:** `https://agent-security-gate-x402-212942243360.asia-northeast3.run.app/hub/`  
> **Registry:** [![npm version](https://img.shields.io/npm/v/agrid-sdk.svg?style=flat-square)](https://www.npmjs.com/package/agrid-sdk)

---

## 📦 Overview

`agrid-sdk` is the official **all-in-one unified SDK** for the A.GRID autonomous machine economy.  
Instead of installing fragmented individual packages, install `agrid-sdk` once to access all 3 foundational domains:

```bash
npm install agrid-sdk
```

---

## 🛠️ Unified Architecture & Subpath Imports

### 1. 🛡️ Security Gate (`agrid-sdk/security`)
Deterministic local prompt injection interception, AST dangerous code execution blocks, bounded Safe multisig execution, and multi-chain task escrow arbitration.

```typescript
import { securityGatePlugin, localSecurityGate } from "agrid-sdk/security";

// ElizaOS Plugin Integration
character.plugins = [securityGatePlugin];

// Standalone Pre-flight Safety Inspection (<1ms)
const audit = localSecurityGate.inspectPayload("Analyze Uniswap pool data");
if (!audit.isSafe) {
  console.error("Blocked injection:", audit.threats);
}
```

### 2. ⚡ CleanWeb Studio (`agrid-sdk/cleanweb`)
87% token-compressed ad-free web intelligence, fresh ground truth extraction, and Solana x402 sub-second autonomous micropayments.

```typescript
import { cleanWebPlugin, scrapeWebAction } from "agrid-sdk/cleanweb";

character.plugins = [cleanWebPlugin];
```

### 3. ⛏️ Critical Minerals Oracle (`agrid-sdk/minerals`)
Autonomous provenance verification, US NDAA Sec 848 defense procurement screening (Tungsten/NdPr), EUDR satellite verification, and M2M trade deal notarization.

```typescript
import { MineralsOracleClient, createMineralsOracleTools } from "agrid-sdk/minerals";

const client = new MineralsOracleClient();
const proof = await client.verifyTungsten({
  batch_id: "W-2026-KR-001",
  mine_origin: "Almonty Sangdong",
  wo3_grade: 89.2
});
console.log("Verified Origin:", proof.status);
```

---

## 🚀 All-in-One Quickstart

```typescript
import { security, cleanweb, minerals } from "agrid-sdk";

// Access all 3 domains seamlessly from the master root
console.log("A.GRID Modules Initialized:", {
  securityActive: Boolean(security.securityGatePlugin),
  cleanwebActive: Boolean(cleanweb.cleanWebPlugin),
  mineralsActive: Boolean(minerals.MineralsOracleClient),
});
```

---

## 🏛️ Institutional Legal, Accounting & Data Governance (`A.GRID-GOV-2026.1`)

A.GRID is built specifically for **lawful, rational, and audit-ready enterprise adoption**:

| Domain | Statutory Retention vs. Privacy Erasure | Corporate Accounting & Anti-Bribery (`IFRS-15 / GAAP / FCPA`) |
| :--- | :--- | :--- |
| **🌲 EUDR & ⛏️ Minerals** | **5-Year Mandatory Audit Vault (`1,825 Days`)** under `EUDR Art. 9(3)/12(5)`, `Reg. (EU) 2017/821`, and `GDPR Art. 17(3)(b)` *(Legal Obligation Exception)* + **0s Immediate RAM Key Scrub** (`NIST-SP-800-88-Rev1`) | **100% Rebate & Kickback Prohibited (`$0.00`)** — Issues clean, ERP-ready corporate invoices with zero third-party kickbacks. |
| **⚡ CleanWeb & 🛡️ Security Gate** | **0s Immediate Payload & PII Zeroization (`0 Years`)** under `GDPR Art. 17(1)` and `NIST-SP-800-88-Rev1` — only the $O(1)$ cryptographic receipt hash remains. | **Enterprise B2B: 0% Rebate Clean Invoice**.<br>**Individual B2C Only**: Strict 1-tier direct affiliate credit (`SINGLE_TIER_1_ONLY`, no multi-level chains). |

---

## 📜 License
MIT © A.GRID & nohosa001-pixel
