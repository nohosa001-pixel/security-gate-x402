# 🛡️ Threat Defense Matrix & Security Taxonomy

This document outlines the deterministic inspection rules, mathematical risk scoring, and multi-tier defense architecture employed by **The Sheriff of Agent Finance (`agent-security-gate-x402`)** and **`@elizaos/plugin-security-gate`**.

---

## 🎯 Defense Overview

Autonomous agents are susceptible to prompt injection, malicious AST code generation, hallucinated calldata, and infinite execution loops. The Security Gate operates as a **Defense-in-Depth Pipeline**:

```
[Inbound Message]
       │
       ▼
1. Zero-Width & Null-Byte Normalization (Strip \0, \u200B, \u200C, \uFEFF)
       │
       ▼
2. Deterministic Regex & Keyword Scanner (<1ms Local Gate)
       ├──> High-Risk Threat Detected? ──> [FAIL-CLOSED: BLOCK]
       │
       ▼
3. AST Code Sandbox & Hazardous Token Analyzer
       ├──> Dangerous Syscall / eval? ──> [FAIL-CLOSED: BLOCK]
       │
       ▼
4. (Optional) Remote Micro-Oracle / NLI Hallucination Verification
       ├──> Discrepancy > 80%? ──────────> [FAIL-CLOSED: BLOCK]
       │
       ▼
5. Cryptographic EIP-712 Attestation Issued (v, r, s Calldata)
       │
       ▼
6. On-Chain Smart Contract Guard (`SafeSecurityGateGuard.sol`)
       └──> Valid Signature Verified ───> [TRANSACTION EXECUTED]
```

---

## 🔬 15+ Adversarial Threat Vectors Intercepted

| # | Threat Category | Attack Vector & Signature | Risk Score | Mitigation Mechanism |
| :-: | :--- | :--- | :-: | :--- |
| **1** | **Direct Instruction Override** | `ignore (all) (previous\|prior) instructions` | **90%** | Regex token boundary matching & immediate turn short-circuit |
| **2** | **DAN Persona Jailbreak** | `you are now in dan mode`, `do anything now` | **95%** | Persona breakout heuristic scanner |
| **3** | **Developer Mode Bypass** | `developer mode (enabled\|activated)` | **85%** | Safety filter override signature detector |
| **4** | **Filter Circumvention** | `bypass (safety\|content\|security) filters` | **90%** | Explicit evasion intent classifier |
| **5** | **System Tag Spoofing** | `<system>`, `[SYSTEM]`, `system: override` | **85%** | Delimiter & prompt structure spoofing detector |
| **6** | **Rule Disregard** | `disregard (all) (system\|rules\|guidelines)` | **90%** | Policy suspension detection filter |
| **7** | **Zero-Width Unicode Evasion** | `\u200B`, `\u200C`, `\u200D`, `\uFEFF`, `\u2060` | **N/A (Pre)** | Stripped in O(N) pre-processing pass prior to evaluation |
| **8** | **Null-Byte Poisoning** | `\0`, `\x00` character insertion | **N/A (Pre)** | Sanitized and stripped from memory strings |
| **9** | **Destructive Shell Commands** | `rm -rf`, `del /f`, `format [a-z]:` | **98%** | Deterministic command regex scanner |
| **10** | **Process Execution (AST)** | `subprocess.Popen`, `os.system`, `subprocess.run` | **95%** | AST syntax tree walk & dangerous function call block |
| **11** | **Dynamic Code Evaluation** | `eval(`, `exec(`, `compile(`, `__import__` | **95%** | Dynamic code execution block |
| **12** | **Encoded Script Execution** | `powershell.exe -enc`, `bash -c base64` | **95%** | Base64-encoded command argument matching |
| **13** | **Private Key & Secret Leak** | `0x[a-f0-9]{64}`, `xprv[a-zA-Z0-9]+` | **99%** | Cryptographic secret regex matcher with hex verification |
| **14** | **AWS / Cloud Secret Leaks** | `AKIA[0-9A-Z]{16}`, `ghp_[a-zA-Z0-9]{36}` | **99%** | API key and token entropy pattern detector |
| **15** | **Factual Hallucination (NLI)** | Fabricated figures or conflicting contract addresses | **85%** | Cross-encoder Natural Language Inference against ground truth |
| **16** | **Treasury Depletion Loop** | Rapid repeated transactions draining gas or funds | **90%** | Rate-limiting velocity checks & spend guard bounds |

---

## ⚡ Latency Benchmarks

All deterministic checks are engineered for sub-millisecond execution to ensure zero impact on conversational responsiveness:

| Component | Average Execution Latency | Dependency |
| :--- | :--- | :--- |
| **Null-Byte & Unicode Normalization** | `< 0.05 ms` | Native string transformation |
| **Local Regex & Injection Scanner** | `< 0.30 ms` | In-memory compiled RegExp |
| **Local AST Hazard Parser** | `< 0.80 ms` | Deterministic token parser |
| **Total Inbound Pre-Handler Overhead** | **< 1.20 ms** | **100% Local (0 Network Calls)** |
| **Remote Micro-Oracle Inspection** | `~8 - 12 ms` | High-throughput Cloud Run micro-service |
| **EIP-712 Cryptographic Attestation** | `~2 - 4 ms` | secp256k1 on-chain signer |

---

## 🛡️ Fail-Closed Principle

1. **Local Analyzer Error**: If an internal regex or parsing error occurs, the default behavior is **FAIL-CLOSED** (`verdict: BLOCK`, `risk_score: 100`).
2. **Remote Oracle Timeout**: In remote mode, network calls enforce an `AbortSignal.timeout(3000)`. If a timeout occurs, the system logs a warning and immediately falls back to the deterministic local verdict without hanging the agent.
3. **On-Chain Guard Enforcement**: Transactions submitted to smart contract accounts lacking a valid EIP-712 attestation signature revert with `InvalidAttestationSignature()` before state modification.
