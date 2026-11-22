# PR Draft: `coinbase/x402` — Add A.GRID Security Gate to Ecosystem Directory (`Services/Endpoints`)

## Target Repository
https://github.com/coinbase/x402

## PR Title
`ecosystem: add A.GRID Security Gate (Services/Endpoints) on Base Mainnet`

## Files Added
1. `typescript/site/app/ecosystem/partners-data/agrid-security-gate/metadata.json`
2. `typescript/site/public/logos/agrid-security-gate.svg`

## PR Description
Adds **A.GRID Security Gate** (`agent-security-gate-x402`) to the x402 Ecosystem Directory under `Services/Endpoints`.

### Overview
- **Category**: `Services/Endpoints`
- **Live Hub**: https://agent-security-gate-x402-212942243360.asia-northeast3.run.app/hub/
- **Base Mainnet x402 Challenge (`chain_id=8453`)**: https://agent-security-gate-x402-212942243360.asia-northeast3.run.app/api/v1/gate/challenge?chain_id=8453
- **Paid Audit Endpoint (`$0.002 USDC` on Base)**: `POST https://agent-security-gate-x402-212942243360.asia-northeast3.run.app/api/v1/escrow/audit`
- **Base Mainnet Deployments**:
  - **ERC-8004 Agent ID**: `#1203885` (`eip155:8453:0x8004A169FB4a3325136EB29fA0ceB6D2e539a432`, [Tx](https://basescan.org/tx/0x2563b73e09eb639c72d290d7041947300b57d0cd03fb1f7a2acd2f8332cca8fd))
  - **UniversalEscrowCore.sol**: `0x745F7FAfFdb626B931Fe769476a09125cbf9d94b` (Verified on BaseScan)
  - **AgentEscrow.sol**: `0x99FEd65Cf2D5378182c3481B300124BB1a8Ad278` (Verified on BaseScan)
  - **ERC-8004 Registration JSON**: https://agent-security-gate-x402-212942243360.asia-northeast3.run.app/.well-known/erc8004-registration.json
