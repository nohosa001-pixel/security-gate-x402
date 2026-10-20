# 🌐 A.GRID SDK (`agrid-sdk`)

> **Unified Master SDK & Runtime Substrate for Autonomous AI Agent Economies**  
> **Ecosystem:** Solana Mainnet (0.4s) • Polygon • Base • Arbitrum • ElizaOS  
> **Live Hub:** `https://agent-security-gate-x402-212942243360.asia-northeast3.run.app/hub/`  

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

## 📜 License
MIT © A.GRID & nohosa001-pixel
