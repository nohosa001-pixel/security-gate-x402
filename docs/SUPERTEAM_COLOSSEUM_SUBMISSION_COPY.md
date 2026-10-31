# 📋 Superteam Microgrant (`<$10k`) & Colosseum Application — Copy & Paste Sheet

> 이 문서는 **Superteam Earn (Microgrants)** 및 **Colosseum Hackathon / Accelerator** 온라인 지원서 양식에 **그대로 복사·붙여넣기(Copy & Paste)** 할 수 있도록 항목별로 최적화된 공식 영문 답변서입니다.

---

## 1. Basic Project Info (기본 정보)

### 🔹 Project Name

```text
A.GRID & Agent Security Gate x402
```

### 🔹 One-Line Pitch (50~100자 요약)

```text
Sub-5ms Pre-Sign Security Gate & 0.4s Atomic Escrow Settlement Layer for Autonomous AI Agents on Solana.
```

### 🔹 Short Description / Elevator Pitch (280자 트윗 길이 요약)

```text
A.GRID (Agent Security Gate x402) is an autonomous AI agent clearinghouse on Solana. We enforce <5ms AST/prompt-injection inspection and spend controls before Squads v4 / session keys sign transactions, settling verified DePIN & M2M deliverables in 0.4s with 1,560+ monthly SDK downloads.
```

### 🔹 Category / Track

* **Primary:** AI Agents / Infrastructure / Payments (PayFi)
* **Secondary:** DePIN / Security & Auditing

### 🔹 Official Links (지원서 링크 입력란)

* **Live Hub & Dashboard URL:** `https://agent-security-gate-x402-212942243360.asia-northeast3.run.app/hub/`
* **Live API Root (OpenAPI / Swagger):** `https://agent-security-gate-x402-212942243360.asia-northeast3.run.app/docs`
* **GitHub Repository:** `https://github.com/nohosa001-pixel/security-gate-x402`
* **NPM (ElizaOS Plugin - 1,124+ monthly downloads):** `https://www.npmjs.com/package/elizaos-plugin-security-gate`
* **NPM (Solana/Coinbase AgentKit Plugin):** `https://www.npmjs.com/package/agentkit-security-gate`
* **PyPI (Python SDK & MCP Server v2.2.0):** `https://pypi.org/project/agent-security-gate-x402/`
* **Solana Mainnet Treasury / Deployer Wallet:** `411ksMz9RHYVtVMe6RUUErzZYtrU9zzvkgzswKbqx9qp`

---

## 2. Problem & Solution (문제 정의 및 해결책)

### 🔹 What problem are you solving?

```text
As autonomous AI agents (ElizaOS, Solana AgentKit, MCP swarms) and DePIN compute networks scale on Solana, giving agents direct access to hot wallets or session keys introduces three critical risks:

1. Prompt Injection & Wallet Drain: A single poisoned prompt or malicious tool payload (e.g., os.system, unauthorized SPL transfer) can trick an autonomous agent into draining its Solana vault in under a second.
2. Compute Fraud & Hallucination in M2M Trade: When an agent hires another agent or GPU node, paying upfront leads to hallucinated/fake outputs, while paying post-delivery leaves workers exposed to non-payment.
3. Cross-Rail Institutional Friction: Enterprise AI buyers fund treasuries via regulated fiat/EVM rails (Polygon Open Money Stack, Stripe x402) but need sub-second micro-streaming settlement on Solana Mainnet (Chain ID 501).
```

### 🔹 How does A.GRID & Agent Security Gate x402 solve this on Solana?

```text
We provide a deterministic Pre-Sign Security Gate + Universal Anchor Escrow protocol built specifically for Solana's 0.4s finality:

1. <5ms Pre-Sign Security Gate: Before an agent's Solana keypair or Squads v4 ephemeral session key signs any transaction, our gate inspects the AST payload, blocks prompt injections, enforces team-set spend limits ($5,000/tx, $25,000/day), and issues an Ed25519/EIP-191 cryptographic attestation.
2. Dual Solana Anchor Programs & Squads v4 CPI:
   - universal_escrow (AGR3W3R9pKxnuZGYrpaggfkbMKVrjoniLaGvi1voBFSC): Enforces 10-30% worker collateral staking, verifies Truth Oracle signatures across 7 sectors (Compute, M2M Code, Trade, Bio, Construction, Power, Logistics), and settles SPL USDC in 0.4s (99.75% to worker, 0.20% treasury, 0.05% referral rebate) or slashes stake on fraud.
   - agent_security_gate (AGRAtNxF474xZFin5iZaxBKE2fKNKPih7qYPEm3mu9oN): On-chain pre-sign policy guard for autonomous Solana vaults.
3. Polygon Open Money Stack (OMS) × Solana Bridge: Enables regulated US/EU/MXN fiat and Polygon USDC treasuries to settle directly into Solana SPL USDC in a single policy-guarded workflow.
```

---

## 3. Traction & Proof of Work (실증 지표 및 왜 지금인가?)

### 🔹 What have you built so far & what is your current traction?

```text
Note: We were directly referred to Superteam Microgrants and Colosseum by the Solana Foundation Grants Team ("while we feel the idea is a good one... we wanted to point you in the direction of Colosseum and Superteam microgrants"). Since our initial submission, we have shipped and verified major production milestones:

1. Live Developer Adoption (1,560+ Monthly Package Downloads):
   - elizaos-plugin-security-gate@2.9.0 on NPM: 1,124+ monthly downloads
   - cleanweb-eliza-plugin@1.0.0 on NPM: 406+ monthly downloads
   - agentkit-security-gate@1.1.0 & minerals-oracle-x402@1.6.0 on NPM
   - agent-security-gate-x402@2.2.0 on PyPI (Python SDK & FastMCP Server)

2. Complete Solana Anchor Codebase & 410 Passing Automated Tests:
   - Full Rust/Anchor source for universal_escrow and agent_security_gate in contracts/solana/programs/
   - Squads v4 ephemeral session-key CPI adapter (app/solana_squads_adapter.py)
   - Polygon OMS × Solana cross-rail pre-sign adapter (app/polygon_oms_adapter.py)
   - 410 / 410 automated pytest unit & integration tests passing

3. Verified On-Chain Multi-Rail Contracts:
   - SecurityGateOMSPolicy.sol deployed & verified on PolygonScan Mainnet: 0x4A28F9A2E6D0DcB69791980560FC8364A514f205
   - UniversalEscrowCore.sol verified on Polygon (0x4Dbd...EAa8), Base (0x745F...d94b), and Arbitrum (0x745F...d94b)

4. 24/7 ElizaOS Brain Continuous Shadow Learning Engine:
   - Live autonomous calibration daemon at Cycle #108+, Readiness 87.21%, Brier Score 0.076, and 12.78ms inference latency.
```

---

## 4. Grant Request & Milestone Breakdown (예산 및 마일스톤)

### 🔹 Requested Grant Amount (Superteam Microgrant Track)

```text
$9,500 USDC
```

### 🔹 How will the funds be used? (3-Week Fast-Track Milestones)

```text
Milestone 1 (Week 1) — $3,000 USDC: Solana Mainnet BPF Deployment & Solscan IDL Verification
- Cover the remaining ~1.71 SOL BPF rent-exemption for deploying universal_escrow (AGR3W3R9pKxnuZGYrpaggfkbMKVrjoniLaGvi1voBFSC) and agent_security_gate (AGRAtNxF474xZFin5iZaxBKE2fKNKPih7qYPEm3mu9oN) as immutable/verified programs on Solana Mainnet-Beta and publish verifiable IDLs on Solscan.

Milestone 2 (Week 2) — $3,500 USDC: Solana AgentKit & ElizaOS Native CPI SDK Expansion
- Ship zero-config TypeScript helpers in agentkit-security-gate and elizaos-plugin-security-gate allowing any Solana agent to lock SPL USDC collateral, request <5ms pre-sign Ed25519 oracle attestations, and execute 0.4s atomic settlement via Squads v4 CPI.

Milestone 3 (Week 3) — $3,000 USDC: Superteam Developer Workshop & 100+ Mainnet Agent Settlements
- Host an open-source workshop for Superteam builders, publish a 5-minute quickstart repo, and execute 100+ verifiable Solana Mainnet x402 agent escrow settlements on Solscan using our 20% protocol fee referral rebate loop.
```

---

## 5. Reply Draft to Solana Foundation Email (선택 사항: 감사 및 진행 공유 답장 초안)

> `grant-apps@solana.org` 메일에 정중히 감사 인사를 남기고, 추천해 준 **Superteam Microgrants** 및 **Colosseum** 트랙을 즉시 진행함과 동시에 새로 달성한 마일스톤(PolygonScan 검증, NPM 1,560+ 다운로드, Polygon OMS × Solana 브릿지)을 기록으로 남겨두기 위한 짧은 영문 답장 초안입니다.

**Subject:** Re: Grant Update | Solana Foundation (A.GRID & Agent Security Gate x402)

```text
Hi Solana Foundation Grants Team,

Thank you very much for taking the time to review our application and for the encouraging feedback and pointers to Colosseum and Superteam Microgrants.

Following your recommendation, we are applying to Superteam Microgrants (<$10k) and preparing for the Colosseum track to complete our Solana Mainnet BPF program deployment and expand our developer traction first.

For your records, since submitting our initial application, we have achieved several major production milestones:
1. Live Developer Adoption: Over 1,560+ monthly NPM downloads across `elizaos-plugin-security-gate@2.9.0` (1,124+/mo) and `cleanweb-eliza-plugin` (406+/mo), plus `agentkit-security-gate@1.1.0` and PyPI `agent-security-gate-x402@2.2.0`.
2. Polygon Open Money Stack (OMS) × Solana Pre-Sign Guard: Built and verified `SecurityGateOMSPolicy.sol` on Polygon Mainnet (0x4A28F9A2E6D0DcB69791980560FC8364A514f205) alongside our Squads v4 Solana CPI adapter (`app/solana_squads_adapter.py`), enabling <5ms pre-sign AST/prompt-injection inspection and cross-rail USDC settlement into Solana Mainnet (Chain ID 501).
3. Continuous AI Calibration: Our ElizaOS Brain shadow-learning engine is live at Cycle #108+ with 87.21% readiness and a 0.076 Brier score across 410 passing automated tests.

Once our dual Anchor programs (`universal_escrow` & `agent_security_gate`) complete full Mainnet BPF deployment and initial Superteam cohort traction, we look forward to sharing our progress with you again.

Best regards,
Seung Il Choi
Founder, A.GRID & Agent Security Gate x402
https://agent-security-gate-x402-212942243360.asia-northeast3.run.app/hub/
https://github.com/nohosa001-pixel/security-gate-x402
```
