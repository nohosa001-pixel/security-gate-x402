# Solana Mainnet Program Verification & IDL Registration Guide ⚡

This guide explains all required files and steps to register and verify the entire **Agent Security Gate x402 & Universal Modular Escrow** suite on Solana Mainnet explorers (**Solscan**, **Solana Explorer**, **SolanaFM**).

> [!IMPORTANT]
> **🔒 보안 점검 원칙 (Security First)**
> 본 가이드와 시스템 설정에는 **사용자의 개인 지갑 비밀키(Private Key)가 절대 사용되거나 노출되지 않습니다.**
> 모든 검증, 수수료 수취(Treasury), 익스플로러 등록은 오직 **공개 키 / 지갑 주소 (Public Address)**로만 수행됩니다.

---

## 📁 1. Solana Registration Files: All 13 Dedicated Contracts & IDLs (1:1 Complete Suite)

All 13 original EVM smart contracts (`contracts/*.sol`) have their own **dedicated Anchor Program ID and individual IDL JSON artifact** for independent registration on Solana:

| # | EVM Contract File | Solana Program ID (32-byte Base58) | Dedicated Explorer IDL JSON | Key Instruction / Account |
| :-: | :--- | :--- | :--- | :--- |
| **1** | [`AgentComplianceRegistry.sol`](../AgentComplianceRegistry.sol) | `AGRGksgAaU1D2cESdYGbFoV4zty3t8D7LacfZ6qcejKe` | [`contracts/solana/idl/AgentComplianceRegistry.json`](idl/AgentComplianceRegistry.json) | `registerCompliance` / `ComplianceRecordAccount` |
| **2** | [`AgentCreditOracle.sol`](../AgentCreditOracle.sol) | `AGRrNBZUAG2CxcxxQW7SGtWY3EMT3JAcVyqwV8ft5GxL` | [`contracts/solana/idl/AgentCreditOracle.json`](idl/AgentCreditOracle.json) | `updateAgentCredit` / `AgentCreditAccount` |
| **3** | [`AgentEscrow.sol`](../AgentEscrow.sol) | `AGRpSZ24g4aWuQsB6zf7F8KvYuySZHnyAwu155mMp26q` | [`contracts/solana/idl/AgentEscrow.json`](idl/AgentEscrow.json) | `createM2mEscrow` / `M2MEscrowAccount` |
| **4** | [`AgentFactoringPool.sol`](../AgentFactoringPool.sol) | `AGRKvCc7edgq1T2KzLwMzUp3S8M8Muy5hv9H7MrZjtEZ` | [`contracts/solana/idl/AgentFactoringPool.json`](idl/AgentFactoringPool.json) | `requestFactoringAdvance` / `FactoringAccount` |
| **5** | [`AgentInsurancePool.sol`](../AgentInsurancePool.sol) | `AGRE6ojRp1pbnYT8QEJ34reGstETHeYGdLncoBc34hQh` | [`contracts/solana/idl/AgentInsurancePool.json`](idl/AgentInsurancePool.json) | `fileInsuranceClaim` / `InsuranceClaimAccount` |
| **6** | [`AgentLendingPool.sol`](../AgentLendingPool.sol) | `AGRuKsgaKpqacjcPvKehAFyfxVQhD3mBUsjfTqL7yGaT` | [`contracts/solana/idl/AgentLendingPool.json`](idl/AgentLendingPool.json) | `borrowCreditLoan` / `CreditLoanAccount` |
| **7** | [`AgentTreasuryVault.sol`](../AgentTreasuryVault.sol) | `AGRUfTxpEKMbG9yxasuoGxGFPp2y3PYEBwEpDUSqpfXQ` | [`contracts/solana/idl/AgentTreasuryVault.json`](idl/AgentTreasuryVault.json) | `depositTreasuryToll` / `TreasuryVaultAccount` |
| **8** | [`GuardableBySecurityGate.sol`](../GuardableBySecurityGate.sol) | `AGR2YR7c5JyL6zmEpZA6rduVTTFSftPKXToeTFj6wQRB` | [`contracts/solana/idl/GuardableBySecurityGate.json`](idl/GuardableBySecurityGate.json) | `guardAccountAccess` / `GuardAccess` |
| **9** | [`ITruthAdapter.sol`](../ITruthAdapter.sol) | `AGReYJAsoJJA7N4wE8oZNgqzhcu6LNnSyBRUMhG8mP7A` | [`contracts/solana/idl/ITruthAdapter.json`](idl/ITruthAdapter.json) | `verifyTruthInterface` / Standard Trait |
| **10** | [`TruthAdapter.sol`](../TruthAdapter.sol) | `AGRCVvz3oYrsPC5vfuWHFPNy9nSqZF54BUXDvRVRhbT` | [`contracts/solana/idl/TruthAdapter.json`](idl/TruthAdapter.json) | `verifyDomainTruth` / `VerifyDomainTruth` |
| **11** | [`SafeSecurityGateGuard.sol`](../SafeSecurityGateGuard.sol) | `AGRAtNxF474xZFin5iZaxBKE2fKNKPih7qYPEm3mu9oN` | [`contracts/solana/idl/SafeSecurityGateGuard.json`](idl/SafeSecurityGateGuard.json) | `verifyMultisigGuard` / `VerifyMultisigGuard` |
| **12** | [`SecurityGateConsumer.sol`](../SecurityGateConsumer.sol) | `AGRivmSTXUQFBgnn3zUDt76qjDJW9Q3W6UVXVPsj6siH` | [`contracts/solana/idl/SecurityGateConsumer.json`](idl/SecurityGateConsumer.json) | `verifyConsumerGate` / `VerifyConsumerGate` |
| **13** | [`UniversalEscrowCore.sol`](../UniversalEscrowCore.sol) | `AGR3W3R9pKxnuZGYrpaggfkbMKVrjoniLaGvi1voBFSC` | [`contracts/solana/idl/UniversalEscrowCore.json`](idl/UniversalEscrowCore.json) | `initializeJob`, `settleJob` / `EscrowJobAccount` |

---

## 🌐 2. On-Chain Metadata & Addresses

* **Network**: Solana Mainnet Beta (`chain_id: 501`)
* **RPC Endpoint**: `https://api.mainnet-beta.solana.com`
* **Native SPL USDC Mint**: `EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v`
* **Deployer / Owner / Treasury Wallet (User Public Key)**: `12CrubUwRKLZAcDsuF3Crh4AfsHtknDcC8RXYXudH4Pd`
* **Oracle Attestation Verifier (Gate Public Key)**: `CG25522QKt3D1K3aSL2fEddj1uq34T3XkPFkZGh4h7ec`

---

## 🛠️ 3. Step-by-Step Registration Instructions

### Method A: SolanaFM Developer Portal & Solscan Web UI (1-Click Safe Registration)
1. Open **[SolanaFM Developer Portal](https://portal.solana.fm)** or **[Solscan.io](https://solscan.io)**
2. Connect your wallet (e.g. Phantom) with your Public Key: `12CrubUwRKLZAcDsuF3Crh4AfsHtknDcC8RXYXudH4Pd`
3. Enter each of the **13 Solana Program IDs** from the table above
4. Upload the matching IDL file from `contracts/solana/idl/` (e.g., `UniversalEscrowCore.json`, `AgentComplianceRegistry.json`, etc.)
5. Once uploaded, the explorer immediately parses instructions and displays interactive verification sandboxes!

### Method B: Anchor CLI (On-Chain IDL Initialization)
If using the Anchor CLI, initialize the on-chain IDL account for any of the 13 programs:
```bash
# Example for Universal Escrow Core
anchor idl init \
  --provider.cluster mainnet \
  --filepath contracts/solana/idl/UniversalEscrowCore.json \
  AGRIDEscrowUniversalMainnet111111111111111111
```


### Method C: OtterSec Verifiable Build (Source Code Verification)
To achieve the green checkmark for source-code verification on Solana:
```bash
# Build verifiable deterministic docker image
anchor build --verifiable

# Verify on OtterSec / SolanaFM
solana-verify verify-from-repo \
  --program-id AGRIDEscrowUniversalMainnet111111111111111111 \
  https://github.com/nohosa001-pixel/security-gate-x402
```
