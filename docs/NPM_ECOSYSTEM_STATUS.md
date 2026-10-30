# 🌐 A.GRID NPM Ecosystem Comprehensive Status Report

> **Generated on:** 2026-10-30  
> **Standard:** A.GRID AP2/1.0 Sovereign Machine-to-Machine NPM Network  
> **Architecture:** OIDC Provenance Cryptographic Publishing & Multi-Repo Master Sync

---

## 1. Live NPM Packages Matrix

| Package | Role | Repo | Local | npm Live | Monthly DL | Dist Status | Sync Status |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **`elizaos-plugin-security-gate`** | ElizaOS Security Gate Guardrails & Local Ingress Defense | `security-gate-x402` | `v2.9.0` | `v2.9.0` | **1,124** | ✅ Ready | 🟢 Synced (Live) |
| **`minerals-oracle-x402`** | Critical Minerals Provenance & M2M Trade Protocol SDK | `minerals-oracle-x402` | `v1.6.0` | `v1.5.0` | **36** | ✅ Ready | 🚀 Update Ready |
| **`agentkit-security-gate`** | Coinbase AgentKit Action Provider for Base Mainnet Escrow | `security-gate-x402` | `v1.1.0` | `v1.0.1` | **0** | ✅ Ready | 🚀 Update Ready |
| **`agrid-sdk`** | A.GRID Master Umbrella SDK (Security + CleanWeb + Minerals) | `security-gate-x402` | `v1.0.0` | `vNot on npm` | **0** | ✅ Ready | ⏳ Pending 1st Publish |
| **`cleanweb-eliza-plugin`** | CleanWeb 87% Token Compression & Ground Truth Intelligence | `x402-micro-agent` | `v1.0.0` | `v1.0.0` | **406** | ✅ Ready | 🟢 Synced (Live) |

---

## 2. CI/CD & Security Invariants

1. **Zero Secret Leakage via OIDC Provenance**:
   - All packages deploy through GitHub Actions using short-lived OpenID Connect tokens directly authenticated with npmjs.org.
2. **Safe Pre-Flight Check**:
   - Every workflow inspects `npm view $NAME@$VERSION` prior to running `npm publish` to prevent pipeline failures on non-bumped commits.
3. **A.GRID Master Umbrella Architecture**:
   - `agrid-sdk` aggregates all three functional domains into unified subpaths (`agrid-sdk/security`, `agrid-sdk/cleanweb`, `agrid-sdk/minerals`).
