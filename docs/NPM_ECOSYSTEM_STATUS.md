# 🌐 A.GRID NPM Ecosystem Comprehensive Status Report

> **Generated on:** 2026-10-28  
> **Standard:** A.GRID AP2/1.0 Sovereign Machine-to-Machine Registry Network  
> **Architecture:** OIDC Provenance Cryptographic Publishing & Multi-Repo Master Sync

---

## 1. Live Packages Matrix (PyPI & NPM)

| Package | Registry | Role | Repo | Local | Live | Dist Status | Sync Status |
| :--- | :---: | :--- | :---: | :---: | :---: | :---: | :---: |
| **`agent-security-gate-x402`** | **PyPI** | Deterministic Security Gate & Multichain Escrow Core | `security-gate-x402` | `v2.1.0` | `v2.1.0` | ✅ Ready | 🟢 Synced (Live) |
| **`elizaos-plugin-security-gate`** | **npm** | ElizaOS Security Gate Guardrails & Multichain Escrow | `security-gate-x402` | `v2.7.0` | `v2.7.0` | ✅ Ready | 🟢 Synced (Live) |
| **`@agrid/agentkit-security-gate`** | **npm** | Coinbase AgentKit Action Provider for Base Mainnet | `security-gate-x402` | `v1.0.0` | `CI Pipeline` | ✅ Built | 🚀 Publishing |
| **`minerals-oracle-x402`** | **npm** | Critical Minerals Provenance & M2M Trade Protocol SDK | `minerals-oracle-x402` | `v1.5.0` | `v1.5.0` | ✅ Ready | 🟢 Synced (Live) |
| **`cleanweb-eliza-plugin`** | **npm** | CleanWeb 87% Token Compression & Ground Truth Intelligence | `x402-micro-agent` | `v1.0.0` | `v1.0.0` | ✅ Ready | 🟢 Synced (Live) |
| **`agrid-sdk`** | **npm** | A.GRID Master Umbrella SDK (Security + CleanWeb + Minerals) | `security-gate-x402` | `v1.0.0` | `vNot on npm` | ✅ Ready | ⏳ Pending 1st Publish |

---

## 2. CI/CD & Security Invariants

1. **Zero Secret Leakage via OIDC Provenance**:
   - All packages deploy through GitHub Actions using short-lived OpenID Connect tokens directly authenticated with npmjs.org.
2. **Safe Pre-Flight Check**:
   - Every workflow inspects `npm view $NAME@$VERSION` prior to running `npm publish` to prevent pipeline failures on non-bumped commits.
3. **A.GRID Master Umbrella Architecture**:
   - `agrid-sdk` aggregates all three functional domains into unified subpaths (`agrid-sdk/security`, `agrid-sdk/cleanweb`, `agrid-sdk/minerals`).
