# 🌐 A.GRID Ecosystem Comprehensive Status Report (PyPI & NPM)

> **Generated on:** 2026-10-24  
> **Standard:** A.GRID AP2/1.0 Sovereign Machine-to-Machine Registry Network  
> **Architecture:** OIDC Provenance Cryptographic Publishing & Multi-Repo Master Sync  
> **Total Ecosystem Traction:** **9,210+ Combined Downloads** (PyPI: 8,302 / NPM: 908)

---

## 1. Live Packages Matrix

| Package | Registry | Role | Repo | Local | Live | Downloads | Dist Status | Sync Status |
| :--- | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **`agent-security-gate-x402`** | **PyPI** | Deterministic Security Gate & Universal Escrow Python Core | `security-gate-x402` | `v2.0.0` | `v2.0.0` | **8,302** (3,640 no-mirror) | ✅ Ready | 🟢 Synced (Live) |
| **`elizaos-plugin-security-gate`** | **npm** | ElizaOS Security Gate Guardrails & Local Ingress Defense | `security-gate-x402` | `v2.6.0` | `v2.6.0` | **896** | ✅ Ready | 🟢 Synced (Live) |
| **`minerals-oracle-x402`** | **npm** | Critical Minerals Provenance & M2M Trade Protocol SDK | `minerals-oracle-x402` | `v1.5.0` | `v1.5.0` | **12** | ✅ Ready | 🟢 Synced (Live) |
| **`cleanweb-eliza-plugin`** | **npm** | CleanWeb 87% Token Compression & Ground Truth Intelligence | `x402-micro-agent` | `v1.0.0` | `v1.0.0` | **0** | ✅ Ready | 🟢 Synced (Live) |
| **`agrid-sdk`** | **npm** | A.GRID Master Umbrella SDK (Security + CleanWeb + Minerals) | `security-gate-x402` | `v1.0.0` | `vNot on npm` | **0** | ✅ Ready | ⏳ Pending 1st Publish |

---

## 2. CI/CD & Security Invariants

1. **Zero Secret Leakage via OIDC Provenance**:
   - All packages deploy through GitHub Actions using short-lived OpenID Connect tokens directly authenticated with npmjs.org.
2. **Safe Pre-Flight Check**:
   - Every workflow inspects `npm view $NAME@$VERSION` prior to running `npm publish` to prevent pipeline failures on non-bumped commits.
3. **A.GRID Master Umbrella Architecture**:
   - `agrid-sdk` aggregates all three functional domains into unified subpaths (`agrid-sdk/security`, `agrid-sdk/cleanweb`, `agrid-sdk/minerals`).
