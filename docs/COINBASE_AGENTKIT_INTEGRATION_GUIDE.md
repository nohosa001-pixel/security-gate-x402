# 🔵 Coinbase AgentKit Action Provider Integration Guide

> **Target Network:** Base Mainnet (Chain ID `8453`)  
> **Official Action Provider:** [`@agrid/agentkit-security-gate`](file:///c:/workspace/security-gate-x402/packages/agentkit-security-gate/) (TypeScript) & [`app/agentkit_provider.py`](file:///c:/workspace/security-gate-x402/app/agentkit_provider.py) (Python)  
> **Base Escrow Core:** `0x99FEd65Cf2D5378182c3481B300124BB1a8Ad278`  
> **Treasury Toll:** 0.25% (20% Referral Rebate to Partner Agents)  
> **Verified Demo:** [`examples/16_coinbase_agentkit_base_escrow_demo.py`](file:///c:/workspace/security-gate-x402/examples/16_coinbase_agentkit_base_escrow_demo.py)

---

## 1. Overview & Value Proposition for Coinbase AgentKit

Coinbase AgentKit enables autonomous agents with crypto wallets (MPC wallets, Base Smart Wallets). However, autonomous agents transacting on Base Mainnet face severe economic risks:
1. **Uncollateralized Counterparty Risk**: Hiring unknown autonomous sub-agents can lead to loss of funds if the agent fails or hallucinates.
2. **Adversarial Code Injection**: Rogue agent outputs can contain malicious AST execution (`os.system`, `subprocess`) or credential exfiltration attempts.
3. **Lack of Truth Anchoring**: No objective, sub-5ms proof-of-delivery oracle to verify deliverables before settlement.

The **Security Gate Action Provider** solves this by enforcing the **Zero-Trust Economic Invariant**:
- Workers must lock **10% ~ 30% collateral** before starting a job.
- Deliverables are deterministically inspected in **< 3ms**.
- Valid deliverables release payouts instantly with on-chain EIP-712 cryptographic proofs.
- Rogue deliverables immediately forfeit the worker's staked collateral to the protocol treasury (`0xA185B43fDD19619f99952AAed6eabf1029bF36a1`).

---

## 2. Action Provider Architecture for `coinbase/agentkit`

```text
┌────────────────────────────────────────────────────────────────────────┐
│                   Coinbase AgentKit Agent Instance                     │
│                (LangChain / AutoGPT / CrewAI / ElizaOS)                │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                     SecurityGateActionProvider                         │
│                                                                        │
│   Action 1: prepare_base_escrow_deposit(job_id, worker, usdc, stake)  │
│   Action 2: inspect_deliverable(job_id, deliverable, spec)            │
│   Action 3: verify_and_settle(job_id, deliverable, spec)              │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                      ┌─────────────┴─────────────┐
                      │                           │
                      ▼                           ▼
        [Deliverable Verified]           [Malicious AST Detected]
                      │                           │
          Release Escrow Payout         Forfeit Worker Collateral
        (Base Mainnet 0x99FEd...)        (Slashed to 0xA185B43...)
```

---

## 3. Installation & Setup

### Python (AgentKit Python SDK)
```bash
pip install "agent-security-gate-x402>=2.1.0"
```

### TypeScript / Node (AgentKit Core)
```bash
npm install @agrid/agentkit-security-gate viem
```

---

## 4. End-to-End Code Walkthrough

### Step 1: Initialize Provider & Deposit Escrow
```python
from app.agentkit_provider import SecurityGateAgentKitProvider, BASE_ESCROW_CORE

provider = SecurityGateAgentKitProvider(
    chain_id=8453, # Base Mainnet
    escrow_contract=BASE_ESCROW_CORE
)

# Prepare 100 USDC escrow with 15% worker collateral
escrow_calldata = provider.prepare_base_escrow_deposit(
    job_id=9021,
    worker_address="0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
    payment_amount_usdc=100.0,
    worker_stake_bps=1500, # 15% collateral
    referral_agent_address="0x15d34AAf54267DB7D7c367839AAf71A00a2C6A65"
)
```

### Step 2: Settle or Slash Based on Deliverable
```python
# Worker submits deliverable
worker_output = '{"dataset_cleaned": true, "records": 50000}'

settlement = provider.verify_and_settle(
    job_id=9021,
    deliverable=worker_output,
    ground_truth_spec="Clean dataset with >= 50,000 verified rows"
)

if settlement["status"] == "APPROVED":
    print("✅ Payout Released with Attestation:", settlement["attestation"]["signature"])
else:
    print("🚨 Threat Detected! Collateral Slashed:", settlement["threats"])
```

---

## 5. Submitting to Coinbase AgentKit Community Directory

This guide and package are structured to submit directly to `coinbase/agentkit` under `cdp-langchain` / `agentkit-actions`:
1. **Repository:** `nohosa001-pixel/security-gate-x402`
2. **Action Provider Class:** `SecurityGateActionProvider`
3. **Category:** Security, Guardrails, & On-Chain Escrow Clearing
4. **Supported Networks:** Base Mainnet (`8453`), Base Sepolia (`84532`)
