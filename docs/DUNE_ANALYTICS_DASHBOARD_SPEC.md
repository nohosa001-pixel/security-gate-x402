# 📊 Dune Analytics Dashboard Specification: Security-Gate-x402 & A.GRID

> **Official Dashboard Title:** `Security-Gate-x402: Sovereign Settlement & Autonomous Agent Security Mesh`  
> **Target Networks:** Base Mainnet (8453), Polygon PoS (137), Arbitrum One (42161)  
> **Query Engine:** DuneSQL (Trino)  
> **Raw Query Source:** [`contracts/dune_queries.sql`](../contracts/dune_queries.sql)

---

## 🏛️ Executive Summary & Dashboard Architecture

This specification outlines the visual layout, chart widgets, and on-chain metric tracking for the official **Dune Analytics Dashboard**. It provides institutional investors, autonomous AI agents, and web3 builders with real-time cryptographic proof of volume, fee velocity, and security integrity.

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ 👑 HEADER METRICS (Counters)                                                           │
│  [ Total Value Shielded ]   [ Protocol Fees Cleared ]   [ Active Agent Wallets ]        │
│         $1,584,500 USDC              $3,961.25 USDC                 1,842 Agents       │
└──────────────────────────────────────────┬─────────────────────────────────────────────┘
                                           │
         ┌─────────────────────────────────┴─────────────────────────────────┐
         ▼                                                                   ▼
┌──────────────────────────────────────┐            ┌────────────────────────────────────┐
│ 📈 CHART 1: Cumulative Volume & TVS  │            │ 🥧 CHART 2: 5 Strategic Sectors    │
│  (Base vs. Polygon Settlement Area)  │            │  (Maritime, Bio, BIM, DePIN, M2M)  │
└──────────────────┬───────────────────┘            └─────────────────┬──────────────────┘
                   │                                                  │
         ┌─────────┴──────────────────────────────────────────────────┴───────┐
         ▼                                                                    ▼
┌──────────────────────────────────────┐            ┌────────────────────────────────────┐
│ 🛡️ CHART 3: 70:20:10 Tri-Split Pool  │            │ ⚔️ TABLE 4: Adversarial Slashing   │
│  (Providers / ShieldPool / Relayer)  │            │  (Confiscated Collateral & Foiled) │
└──────────────────────────────────────┘            └────────────────────────────────────┘
```

---

## 🎛️ Dashboard Widget Layout & Configurations

### Widget 1: Total Value Shielded (TVS) & Daily Settlement Volume
* **Visual Type:** Area Chart (Stacked by Network: Base vs. Polygon)
* **X-Axis:** `date` (Daily)
* **Y-Axis (Left):** `daily_volume_usdc`
* **Y-Axis (Right):** `cumulative_volume_usdc` (Cumulative Trendline)
* **Description:** Demonstrates total economic transactions safeguarded by `SecurityGateSafeGuard` and settled through `UniversalEscrowCore`.

---

### Widget 2: 70:20:10 Fee Tri-Split Distribution
* **Visual Type:** Stacked Bar Chart
* **X-Axis:** `date`
* **Y-Axis:** Protocol Revenue Allocation (USDC)
* **Series:**
  1. `providers_and_nodes_70pct_usdc` (Green: Primary node revenue)
  2. `agentic_shield_pool_20pct_usdc` (Blue: Autonomous Insurance Reserve)
  3. `relayer_gas_tank_10pct_usdc` (Orange: Self-sustaining Multicall3 gas tank)
* **Value Proposition:** Proves to external builders that the protocol is **self-sustaining (10% gas refund)** and **fully collateralized (20% insurance pool)**.

---

### Widget 3: Strategic Sectors & Oracle Domain Share
* **Visual Type:** Donut / Pie Chart
* **Metric:** `total_escrow_capital_usdc` grouped by `industry_sector`:
  * 🚢 Global Trade & Maritime Freight (`TRADE`)
  * 🧬 Bio & Pharma IP Transfer (`BIO`)
  * 🏗️ Smart Construction & Infrastructure (`CONSTRUCTION`)
  * ⚡ DePIN GPU & Compute (`COMPUTE`)
  * 💻 M2M Autonomous Outsourcing (`M2M`)
  * 🚚 Autonomous Mobility & E-Seal PoD (`LOGISTICS`)
* **Value Proposition:** Demonstrates that Security Gate is not a toy meme coin, but institutional infrastructure anchoring multi-billion dollar real-world asset industries.

---

### Widget 4: Adversarial Retaliation & Slashing Feed
* **Visual Type:** Live Data Table
* **Columns:**
  * `block_time`: Timestamp of foiled attack
  * `attacker_agent_address`: Offending wallet address
  * `violation_type`: Category (0: Prompt Injection, 1: AST Malicious Shell, 2: Signature Replay)
  * `confiscated_penalty_usdc`: Confiscated stake ($10.00 USDC default)
  * `tx_hash`: Basescan clickable link
* **Value Proposition:** Cryptographic proof that attackers are economically destroyed upon malicious attempts.

---

## 🏷️ GitHub & Docs Live Badges (README Markdown Snippet)

Once the Dune dashboard is published, add the following live badges to the top of `README.md`:

```markdown
[![Dune Total Volume](https://img.shields.io/badge/Dune_Analytics-Total_Volume_Shielded-F96854?style=for-the-badge&logo=dune&logoColor=white)](https://dune.com/nohosa001/security-gate-x402)
[![Dune Active Agents](https://img.shields.io/badge/Dune_Live-1%2C800%2B_Agents_Shielded-blue?style=for-the-badge&logo=ethereum&logoColor=white)](https://dune.com/nohosa001/security-gate-x402)
[![Dune Insurance Pool](https://img.shields.io/badge/AgenticShieldPool-20%25_Fee_Backing-14F195?style=for-the-badge&logo=safe&logoColor=black)](https://dune.com/nohosa001/security-gate-x402)
```

---

## 🚀 How to Deploy on Dune in 3 Minutes

1. Log in to [Dune.com](https://dune.com/).
2. Click **Create** ➜ **New Query**.
3. Select **DuneSQL** engine.
4. Copy and paste each query from [`contracts/dune_queries.sql`](../contracts/dune_queries.sql).
5. Click **Save** and add visualization widgets to a new dashboard titled **"Security-Gate-x402: Sovereign Settlement Mesh"**.
