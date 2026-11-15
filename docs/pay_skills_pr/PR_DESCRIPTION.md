# PR Draft: `solana-foundation/pay-skills` — Add `agrid/security-gate` (`category: security`)

## Target Path in `solana-foundation/pay-skills`
`providers/agrid/security-gate/PAY.md`

## PR Title
`feat(providers): add agrid/security-gate x402 pre-sign security oracle (category: security)`

## PR Summary
- **Category**: `security`
- **Provider**: A.GRID (`agent-security-gate-x402`)
- **Payment Protocol**: HTTP `402` (`x402`) with Solana Mainnet USDC (`EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v`, `$0.002` / `2000` micro-units)
- **Live Endpoint**: `https://agent-security-gate-x402-212942243360.asia-northeast3.run.app/api/v1/escrow/audit`
- **x402 Challenge Endpoint**: `https://agent-security-gate-x402-212942243360.asia-northeast3.run.app/api/v1/x402/challenge?chain_id=501`
- **Solana Mainnet 8004 Identity**:
  - Asset Pubkey: `yrvkHggv4ScF5fUfBnKEtg4BkCL26qPKzHV445bRMU9`
  - Registration Tx: `RpofwkoDz1Vk5CoskqumHDPCM11dxTDnwqwina34cWuXTmWUT3kXkvfnGZ8u3Wd5tJW1Gzcinyuv8Zm4TRg83dL`
- **Verification**:
  - `/.well-known/erc8004-registration.json` returns `200 OK`
  - `GET /api/v1/x402/challenge?chain_id=501` returns `402 Payment Required` with Solana USDC (`EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v`)

