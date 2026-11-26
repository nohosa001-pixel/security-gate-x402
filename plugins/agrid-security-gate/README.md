# A.GRID Security Gate

**Non-custodial Pre-Settlement Security Gate and 5-Chain Counterparty KYW/USDC Solvency Oracle for autonomous AI agents.**

A.GRID connects directly to the live remote HTTPS MCP gateway (`https://agent-security-gate-x402-212942243360.asia-northeast3.run.app/mcp`) with zero local runtime dependencies.

## Included Components

- **Remote MCP Server (`gateway`)**: Exposes 18 deterministic security, KYW/solvency, credit rating, and attestation tools over HTTPS.
- **Skill (`/agrid-security-gate`)**: Guides agents to audit prompts, Python AST code, shell commands, and counterparty wallets before signing transactions.

## Key Capabilities

- **Sub-3ms Pre-Sign Firewall**: Blocks prompt injection, secret/private-key leakage, dangerous Python AST operations, and shell exfiltration.
- **5-Chain Counterparty KYW & USDC Solvency (`verify_counterparty_kyw_solvency`)**: Screens OFAC/mixer risk and verifies live on-chain USDC & gas balances across **Solana (`501`)**, **Polygon (`137`)**, **Base (`8453`)**, **Arbitrum (`42161`)**, and **Ethereum (`1`)**.
- **On-Chain Spend Controls & Identity**: Backed by verified Solana Mainnet Anchor programs (`AGR3W3R9...BFSC`, `AGRAtNxF...u9oN`), Polygon `SecurityGateOMSPolicy.sol`, and 4-chain `8004` agent identity.

## Example Prompts

- *"Audit this prompt and Python snippet for injection or credential exfiltration"*
- *"Verify counterparty wallet KYW sanctions and live USDC solvency on Solana or Base"*
- *"Check ERC-8004 agent credit rating and pre-sign spend policy before signing"*

## Links

- Live Hub: https://agent-security-gate-x402-212942243360.asia-northeast3.run.app/hub/
- API Docs: https://agent-security-gate-x402-212942243360.asia-northeast3.run.app/docs
- Source Repository: https://github.com/nohosa001-pixel/security-gate-x402
