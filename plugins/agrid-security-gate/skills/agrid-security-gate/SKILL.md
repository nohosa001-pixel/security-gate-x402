---
name: agrid-security-gate
description: >-
  Inspect prompts, Python AST code, shell commands, and counterparty wallets
  (OFAC/mixer screening + live 5-chain USDC solvency across Solana, Polygon,
  Base, Arbitrum, and Ethereum) before autonomous agents execute or sign
  transactions. Use when auditing untrusted agent inputs, verifying wallet
  solvency/sanctions, or checking pre-sign spend controls.
license: MIT
---

# A.GRID Security Gate & Counterparty KYW/Solvency Tollgate

Use the bundled `gateway` MCP server (`https://agent-security-gate-x402-212942243360.asia-northeast3.run.app/mcp`) to enforce deterministic pre-sign and pre-settlement guardrails before executing untrusted actions or transferring funds.

## Core Workflows

1. **Prompt, Code & Shell Safety (`<3ms`)**
   - Call `verify_agent_output` for rapid prompt-injection, jailbreak, and secret/key-leak screening.
   - Call `inspect_code_ast_safety` before running untrusted Python snippets (`os.system`, `subprocess`, `eval`, `exec`, socket exfiltration).
   - Call `inspect_shell_command_safety` before executing shell commands.

2. **Pre-Settlement Counterparty KYW & Multi-Chain USDC Solvency**
   - Call `verify_counterparty_kyw_solvency` with `counterparty_address`, `chain_id` (`501` Solana, `137` Polygon, `8453` Base, `42161` Arbitrum, `1` Ethereum), `required_amount_usdc`, and optional `payload_to_audit`.
   - Reject or halt settlement whenever `verdict` is `"REJECTED"` (`SANCTIONED_OR_MIXER_ADDRESS`, `INSUFFICIENT_USDC`, `SECURITY_GATE_BLOCKED`, or low credit grade).

3. **On-Chain Policy, Credit & Attestation**
   - Call `get_agent_credit_rating` to inspect an EVM wallet's Credit Rating Score (CRS).
   - Call `verify_polygon_oms_solana_payment` or `get_onchain_security_attestation` to enforce spend limits and produce cryptographic `proof_hash` / EIP-712 attestations.
