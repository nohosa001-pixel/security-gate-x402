# Smart Contract Verification & Public Explorer Guide

This guide provides everything required to verify and publicly display the **Agent Security Gate x402** contracts on block explorers (**Polygonscan**, **BaseScan**, **Arbiscan**).

---

## 1. Quick Verification Parameters

| Parameter | Value |
| :--- | :--- |
| **Compiler Type** | **`Solidity (Standard-Json-Input)`** ⭐ (권장 - 메타데이터 100% 일치) |
| **Alternative (간단한 컨트랙트용)** | `Solidity (Single file)` |
| **Solidity Compiler Version** | `v0.8.20+commit.a1b79de6` |
| **Open Source License Type** | `MIT License (MIT)` |
| **Optimization** | `No` (최적화 안 함 / False) |
| **EVM Version** | `default` |

> 💡 **중요 안내**: OpenZeppelin 라이브러리를 import하는 복합 컨트랙트(`AgentLendingPool`, `AgentEscrow` 등)는 Single file로 검증 시 컴파일러 메타데이터(IPFS 해시) 불일치로 인해 `Error! Unable to Verify Contract Source Code` 오류가 발생합니다. 반드시 **`Solidity (Standard-Json-Input)`**를 선택하고 생성된 `*.standard.json` 파일을 업로드해야 합니다.

---

## 2. Polygon Mainnet (Chain ID: 137)

### Contract 1: `SafeSecurityGateGuard.sol` (Core ERC-712 Guard)

* **Status**: ✅ **Verified on Polygonscan**
* **Deployed Address**: [`0x5cC5Afa2a97599d492A3E408Fdd95fD0b520f173`](https://polygonscan.com/address/0x5cC5Afa2a97599d492A3E408Fdd95fD0b520f173#code)
* **Direct Verification URL**: [https://polygonscan.com/verifyContract?a=0x5cC5Afa2a97599d492A3E408Fdd95fD0b520f173](https://polygonscan.com/verifyContract?a=0x5cC5Afa2a97599d492A3E408Fdd95fD0b520f173)
* **Source File**: [`contracts/verification/SafeSecurityGateGuard.flattened.sol`](SafeSecurityGateGuard.flattened.sol)
* **Constructor Arguments**:
  * `_oracleSigner`: `0x255F9991233f86B29dB847c8d5b8CB9915e80dCf`
  * `_maxAllowedRiskScore`: `30`
* **ABI-Encoded Constructor Arguments (HEX)**:

```text
000000000000000000000000255f9991233f86b29db847c8d5b8cb9915e80dcf000000000000000000000000000000000000000000000000000000000000001e
```

---

### Contract 2: `AgentCreditOracle.sol` (Credit Rating & Risk Oracle)

* **Status**: ✅ **Verified on Polygonscan**
* **Deployed Address**: [`0x6418f408cFf03F862D7691f01fAb00a895E6aB93`](https://polygonscan.com/address/0x6418f408cFf03F862D7691f01fAb00a895E6aB93#code)
* **Direct Verification URL**: [https://polygonscan.com/verifyContract?a=0x6418f408cFf03F862D7691f01fAb00a895E6aB93](https://polygonscan.com/verifyContract?a=0x6418f408cFf03F862D7691f01fAb00a895E6aB93)
* **Source File**: [`contracts/verification/AgentCreditOracle.flattened.sol`](AgentCreditOracle.flattened.sol)
* **Constructor Arguments**:
  * `_oracleSigner`: `0x255F9991233f86B29dB847c8d5b8CB9915e80dCf`
* **ABI-Encoded Constructor Arguments (HEX)**:

```text
000000000000000000000000255f9991233f86b29db847c8d5b8cb9915e80dcf
```

---

### Contract 3: `AgentComplianceRegistry.sol` (EU AI Act Compliance)

* **Status**: ✅ **Verified on Polygonscan**
* **Deployed Address**: [`0x28292D76E07E5539F15F3b97935dE8E0432E76DD`](https://polygonscan.com/address/0x28292D76E07E5539F15F3b97935dE8E0432E76DD#code)
* **Direct Verification URL**: [https://polygonscan.com/verifyContract?a=0x28292D76E07E5539F15F3b97935dE8E0432E76DD](https://polygonscan.com/verifyContract?a=0x28292D76E07E5539F15F3b97935dE8E0432E76DD)
* **Source File**: [`contracts/verification/AgentComplianceRegistry.flattened.sol`](AgentComplianceRegistry.flattened.sol)
* **Constructor Arguments**:
  * `_complianceOracleSigner`: `0x255F9991233f86B29dB847c8d5b8CB9915e80dCf`
* **ABI-Encoded Constructor Arguments (HEX)**:

```text
000000000000000000000000255f9991233f86b29db847c8d5b8cb9915e80dcf
```

---

### Contract 4: `AgentEscrow.sol` (M2M Escrow & Slashing)

* **Status**: ✅ **Verified on Polygonscan**
* **Deployed Address**: [`0x8ACafCEce0B1BFE140e75614b90FD1307b6f389d`](https://polygonscan.com/address/0x8ACafCEce0B1BFE140e75614b90FD1307b6f389d#code)
* **Direct Verification URL**: [https://polygonscan.com/verifyContract?a=0x8ACafCEce0B1BFE140e75614b90FD1307b6f389d](https://polygonscan.com/verifyContract?a=0x8ACafCEce0B1BFE140e75614b90FD1307b6f389d)
* **Source File**: [`contracts/verification/AgentEscrow.flattened.sol`](AgentEscrow.flattened.sol)
* **Constructor Arguments**:
  * `_paymentToken` (Polygon Native USDC): `0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359`
  * `_oracleSigner`: `0x255F9991233f86B29dB847c8d5b8CB9915e80dCf`
* **ABI-Encoded Constructor Arguments (HEX)**:

```text
0000000000000000000000003c499c542cef5e3811e1192ce70d8cc03d5c3359000000000000000000000000255f9991233f86b29db847c8d5b8cb9915e80dcf
```

---

### Contract 5: `AgentLendingPool.sol` (Uncollateralized Micro-Lending)

* **Status**: ✅ **Verified on Polygonscan**
* **Deployed Address**: [`0xe43a9C368808B2dfF139D27789C40A3C8F2282cF`](https://polygonscan.com/address/0xe43a9C368808B2dfF139D27789C40A3C8F2282cF#code)
* **Direct Verification URL**: [https://polygonscan.com/verifyContract?a=0xe43a9C368808B2dfF139D27789C40A3C8F2282cF](https://polygonscan.com/verifyContract?a=0xe43a9C368808B2dfF139D27789C40A3C8F2282cF)
* **Source File**: [`contracts/verification/AgentLendingPool.flattened.sol`](AgentLendingPool.flattened.sol)
* **Constructor Arguments**:
  * `_usdcToken` (Polygon Native USDC): `0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359`
  * `_creditOracle`: `0x6418f408cFf03F862D7691f01fAb00a895E6aB93`
* **ABI-Encoded Constructor Arguments (HEX)**:

```text
0000000000000000000000003c499c542cef5e3811e1192ce70d8cc03d5c33590000000000000000000000006418f408cff03f862d7691f01fab00a895e6ab93
```

---

### Contract 6: `AgentInsurancePool.sol` (Malpractice & Injection Insurance)

* **Status**: ✅ **Verified on Polygonscan**
* **Deployed Address**: [`0xE67F4BC75B11dBb3ef2C9Ad1848B4b193c2c69C6`](https://polygonscan.com/address/0xE67F4BC75B11dBb3ef2C9Ad1848B4b193c2c69C6#code)
* **Direct Verification URL**: [https://polygonscan.com/verifyContract?a=0xE67F4BC75B11dBb3ef2C9Ad1848B4b193c2c69C6](https://polygonscan.com/verifyContract?a=0xE67F4BC75B11dBb3ef2C9Ad1848B4b193c2c69C6)
* **Source File**: [`contracts/verification/AgentInsurancePool.standard.json`](AgentInsurancePool.standard.json)
* **Constructor Arguments**:
  * `_usdcToken`: `0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359`
  * `_oracleSigner`: `0x255F9991233f86B29dB847c8d5b8CB9915e80dCf`
  * `_oracleTreasury`: `0x255F9991233f86B29dB847c8d5b8CB9915e80dCf`
* **ABI-Encoded Constructor Arguments (HEX)**:

```text
0000000000000000000000003c499c542cef5e3811e1192ce70d8cc03d5c3359000000000000000000000000255f9991233f86b29db847c8d5b8cb9915e80dcf000000000000000000000000255f9991233f86b29db847c8d5b8cb9915e80dcf
```

---

### Contract 7: `AgentFactoringPool.sol` (Invoice & Receivables Factoring)

* **Status**: ✅ **Verified on Polygonscan**
* **Deployed Address**: [`0xd0Aa4Aed2AeDE14611B53C3e93CF784F3Fe05BB0`](https://polygonscan.com/address/0xd0Aa4Aed2AeDE14611B53C3e93CF784F3Fe05BB0#code)
* **Direct Verification URL**: [https://polygonscan.com/verifyContract?a=0xd0Aa4Aed2AeDE14611B53C3e93CF784F3Fe05BB0](https://polygonscan.com/verifyContract?a=0xd0Aa4Aed2AeDE14611B53C3e93CF784F3Fe05BB0)
* **Source File**: [`contracts/verification/AgentFactoringPool.standard.json`](AgentFactoringPool.standard.json)
* **Constructor Arguments**: Same as Insurance Pool
* **ABI-Encoded Constructor Arguments (HEX)**:

```text
0000000000000000000000003c499c542cef5e3811e1192ce70d8cc03d5c3359000000000000000000000000255f9991233f86b29db847c8d5b8cb9915e80dcf000000000000000000000000255f9991233f86b29db847c8d5b8cb9915e80dcf
```

---

### Contract 8: `AgentTreasuryVault.sol` (Hedge Fund & Treasury Vault)

* **Status**: ✅ **Verified on Polygonscan**
* **Deployed Address**: [`0xfCf3BF5fB5858db9aE81bE458B39b0032fc0C638`](https://polygonscan.com/address/0xfCf3BF5fB5858db9aE81bE458B39b0032fc0C638#code)
* **Direct Verification URL**: [https://polygonscan.com/verifyContract?a=0xfCf3BF5fB5858db9aE81bE458B39b0032fc0C638](https://polygonscan.com/verifyContract?a=0xfCf3BF5fB5858db9aE81bE458B39b0032fc0C638)
* **Source File**: [`contracts/verification/AgentTreasuryVault.standard.json`](AgentTreasuryVault.standard.json)
* **Constructor Arguments**: Same as Insurance Pool
* **ABI-Encoded Constructor Arguments (HEX)**:

```text
0000000000000000000000003c499c542cef5e3811e1192ce70d8cc03d5c3359000000000000000000000000255f9991233f86b29db847c8d5b8cb9915e80dcf000000000000000000000000255f9991233f86b29db847c8d5b8cb9915e80dcf
```

---

### Contract 9: `SecurityGateConsumer.sol` (End-to-End Showcase Consumer)

* **Status**: ✅ **Verified on Polygonscan**
* **Deployed Address**: [`0x9E3dEE18D8139E1d20f9f7D1F6673c75727F1DDA`](https://polygonscan.com/address/0x9E3dEE18D8139E1d20f9f7D1F6673c75727F1DDA#code)
* **Direct Verification URL**: [https://polygonscan.com/verifyContract?a=0x9E3dEE18D8139E1d20f9f7D1F6673c75727F1DDA](https://polygonscan.com/verifyContract?a=0x9E3dEE18D8139E1d20f9f7D1F6673c75727F1DDA)
* **Source File**: [`contracts/verification/SecurityGateConsumer.flattened.sol`](SecurityGateConsumer.flattened.sol)
* **Constructor Arguments**:
  * `_oracleSigner`: `0x255F9991233f86B29dB847c8d5b8CB9915e80dCf`
* **ABI-Encoded Constructor Arguments (HEX)**:

```text
000000000000000000000000255f9991233f86b29db847c8d5b8cb9915e80dcf
```

---

## 3. Base Mainnet (Chain ID: 8453)

> 💡 **BaseScan 인증 파라미터**:
>
> * **Compiler Type**: `Solidity (Standard-Json-Input)`
> * **Compiler Version**: `v0.8.20+commit.a1b79de6`
> * **Open Source License Type**: `MIT License (MIT)`
> * **업로드 폴더**: [`contracts/verification/base/`](base/)

| # | 컨트랙트 | BaseScan 주소 & 코드 페이지 | 인증 상태 | 업로드 파일 | Constructor HEX |
| :-: | :--- | :--- | :-: | :--- | :--- |
| 1 | **SafeSecurityGateGuard** | [`0x306e69E59E5bCEa769C6CeA76A79AFA8f2A5F408`](https://basescan.org/address/0x306e69E59E5bCEa769C6CeA76A79AFA8f2A5F408#code) | ✅ **Verified** | [`SafeSecurityGateGuard.standard.json`](base/SafeSecurityGateGuard.standard.json) | `000000000000000000000000255f9991233f86b29db847c8d5b8cb9915e80dcf000000000000000000000000000000000000000000000000000000000000001e` |
| 2 | **AgentCreditOracle** | [`0x227e1129Ba9B39a50fb9E0802bA13A7F77Debe93`](https://basescan.org/address/0x227e1129Ba9B39a50fb9E0802bA13A7F77Debe93#code) | ✅ **Verified** | [`AgentCreditOracle.standard.json`](base/AgentCreditOracle.standard.json) | `000000000000000000000000255f9991233f86b29db847c8d5b8cb9915e80dcf` |
| 3 | **AgentTreasuryVault** | [`0xF8e1439F61c9F2d5FdbA382D524FabB35e12ae55`](https://basescan.org/address/0xF8e1439F61c9F2d5FdbA382D524FabB35e12ae55#code) | ✅ **Verified** | [`AgentTreasuryVault.standard.json`](base/AgentTreasuryVault.standard.json) | `000000000000000000000000833589fcd6edb6e08f4c7c32d4f71b54bda02913000000000000000000000000255f9991233f86b29db847c8d5b8cb9915e80dcf000000000000000000000000255f9991233f86b29db847c8d5b8cb9915e80dcf` |
| 4 | **AgentComplianceRegistry** | [`0x821d88Df97F6063a32fDff85FBad9784B9B7292D`](https://basescan.org/address/0x821d88Df97F6063a32fDff85FBad9784B9B7292D#code) | ✅ **Verified** | [`AgentComplianceRegistry.standard.json`](base/AgentComplianceRegistry.standard.json) | `000000000000000000000000255f9991233f86b29db847c8d5b8cb9915e80dcf` |
| 5 | **AgentEscrow** | [`0x99FEd65Cf2D5378182c3481B300124BB1a8Ad278`](https://basescan.org/address/0x99FEd65Cf2D5378182c3481B300124BB1a8Ad278#code) | ✅ **Verified** | [`AgentEscrow.standard.json`](base/AgentEscrow.standard.json) | `000000000000000000000000833589fcd6edb6e08f4c7c32d4f71b54bda02913000000000000000000000000255f9991233f86b29db847c8d5b8cb9915e80dcf` |
| 6 | **AgentInsurancePool** | [`0x90308AedEe6430D11e5214cf9d2F563333D33Ef2`](https://basescan.org/address/0x90308AedEe6430D11e5214cf9d2F563333D33Ef2#code) | ✅ **Verified** | [`AgentInsurancePool.standard.json`](base/AgentInsurancePool.standard.json) | `000000000000000000000000833589fcd6edb6e08f4c7c32d4f71b54bda02913000000000000000000000000255f9991233f86b29db847c8d5b8cb9915e80dcf000000000000000000000000255f9991233f86b29db847c8d5b8cb9915e80dcf` |
| 7 | **AgentLendingPool** | [`0x5cC5Afa2a97599d492A3E408Fdd95fD0b520f173`](https://basescan.org/address/0x5cC5Afa2a97599d492A3E408Fdd95fD0b520f173#code) | ✅ **Verified** | [`AgentLendingPool.standard.json`](base/AgentLendingPool.standard.json) | `000000000000000000000000833589fcd6edb6e08f4c7c32d4f71b54bda02913000000000000000000000000227e1129ba9b39a50fb9e0802ba13a7f77debe93` |
| 8 | **AgentFactoringPool** | [`0x6418f408cFf03F862D7691f01fAb00a895E6aB93`](https://basescan.org/address/0x6418f408cFf03F862D7691f01fAb00a895E6aB93#code) | ✅ **Verified** | [`AgentFactoringPool.standard.json`](base/AgentFactoringPool.standard.json) | `000000000000000000000000833589fcd6edb6e08f4c7c32d4f71b54bda02913000000000000000000000000255f9991233f86b29db847c8d5b8cb9915e80dcf000000000000000000000000255f9991233f86b29db847c8d5b8cb9915e80dcf` |
| 9 | **SecurityGateConsumer** | [`0xdC6Cb774d51681Fcbba0E67Ca677dEc5705aaB35`](https://basescan.org/address/0xdC6Cb774d51681Fcbba0E67Ca677dEc5705aaB35#code) | ✅ **Verified** | [`SecurityGateConsumer.standard.json`](base/SecurityGateConsumer.standard.json) | `000000000000000000000000255f9991233f86b29db847c8d5b8cb9915e80dcf` |

---

## 4. Arbitrum One Mainnet (Chain ID: 42161)

> 💡 **Arbiscan 인증 파라미터**:
>
> * **Compiler Type**: `Solidity (Standard-Json-Input)`
> * **Compiler Version**: `v0.8.20+commit.a1b79de6`
> * **Open Source License Type**: `MIT License (MIT)`
> * **업로드 폴더**: [`contracts/verification/arbitrum/`](arbitrum/)

| # | 컨트랙트 | Arbiscan 주소 & 검증 링크 | 업로드 파일 | Constructor HEX |
| :-: | :--- | :--- | :--- | :--- |
| 1 | **SafeSecurityGateGuard** | [`0x306e69E59E5bCEa769C6CeA76A79AFA8f2A5F408`](https://arbiscan.io/verifyContract?a=0x306e69E59E5bCEa769C6CeA76A79AFA8f2A5F408) | [`SafeSecurityGateGuard.standard.json`](arbitrum/SafeSecurityGateGuard.standard.json) | `000000000000000000000000255f9991233f86b29db847c8d5b8cb9915e80dcf000000000000000000000000000000000000000000000000000000000000001e` |
| 2 | **AgentCreditOracle** | [`0x227e1129Ba9B39a50fb9E0802bA13A7F77Debe93`](https://arbiscan.io/verifyContract?a=0x227e1129Ba9B39a50fb9E0802bA13A7F77Debe93) | [`AgentCreditOracle.standard.json`](arbitrum/AgentCreditOracle.standard.json) | `000000000000000000000000255f9991233f86b29db847c8d5b8cb9915e80dcf` |
| 3 | **AgentTreasuryVault** | [`0xF8e1439F61c9F2d5FdbA382D524FabB35e12ae55`](https://arbiscan.io/verifyContract?a=0xF8e1439F61c9F2d5FdbA382D524FabB35e12ae55) | [`AgentTreasuryVault.standard.json`](arbitrum/AgentTreasuryVault.standard.json) | `000000000000000000000000af88d065e77c8cc2239327c5edb3a432268e5831000000000000000000000000255f9991233f86b29db847c8d5b8cb9915e80dcf000000000000000000000000255f9991233f86b29db847c8d5b8cb9915e80dcf` |
| 4 | **AgentComplianceRegistry** | [`0x821d88Df97F6063a32fDff85FBad9784B9B7292D`](https://arbiscan.io/verifyContract?a=0x821d88Df97F6063a32fDff85FBad9784B9B7292D) | [`AgentComplianceRegistry.standard.json`](arbitrum/AgentComplianceRegistry.standard.json) | `000000000000000000000000255f9991233f86b29db847c8d5b8cb9915e80dcf` |
| 5 | **AgentEscrow** | [`0x99FEd65Cf2D5378182c3481B300124BB1a8Ad278`](https://arbiscan.io/verifyContract?a=0x99FEd65Cf2D5378182c3481B300124BB1a8Ad278) | [`AgentEscrow.standard.json`](arbitrum/AgentEscrow.standard.json) | `000000000000000000000000af88d065e77c8cc2239327c5edb3a432268e5831000000000000000000000000255f9991233f86b29db847c8d5b8cb9915e80dcf` |
| 6 | **AgentInsurancePool** | [`0x90308AedEe6430D11e5214cf9d2F563333D33Ef2`](https://arbiscan.io/verifyContract?a=0x90308AedEe6430D11e5214cf9d2F563333D33Ef2) | [`AgentInsurancePool.standard.json`](arbitrum/AgentInsurancePool.standard.json) | `000000000000000000000000af88d065e77c8cc2239327c5edb3a432268e5831000000000000000000000000255f9991233f86b29db847c8d5b8cb9915e80dcf000000000000000000000000255f9991233f86b29db847c8d5b8cb9915e80dcf` |
| 7 | **AgentLendingPool** | [`0x5cC5Afa2a97599d492A3E408Fdd95fD0b520f173`](https://arbiscan.io/verifyContract?a=0x5cC5Afa2a97599d492A3E408Fdd95fD0b520f173) | [`AgentLendingPool.standard.json`](arbitrum/AgentLendingPool.standard.json) | `000000000000000000000000af88d065e77c8cc2239327c5edb3a432268e5831000000000000000000000000227e1129ba9b39a50fb9e0802ba13a7f77debe93` |
| 8 | **AgentFactoringPool** | [`0x6418f408cFf03F862D7691f01fAb00a895E6aB93`](https://arbiscan.io/verifyContract?a=0x6418f408cFf03F862D7691f01fAb00a895E6aB93) | [`AgentFactoringPool.standard.json`](arbitrum/AgentFactoringPool.standard.json) | `000000000000000000000000af88d065e77c8cc2239327c5edb3a432268e5831000000000000000000000000255f9991233f86b29db847c8d5b8cb9915e80dcf000000000000000000000000255f9991233f86b29db847c8d5b8cb9915e80dcf` |
| 9 | **SecurityGateConsumer** | [`0xdC6Cb774d51681Fcbba0E67Ca677dEc5705aaB35`](https://arbiscan.io/verifyContract?a=0xdC6Cb774d51681Fcbba0E67Ca677dEc5705aaB35) | [`SecurityGateConsumer.standard.json`](arbitrum/SecurityGateConsumer.standard.json) | `000000000000000000000000255f9991233f86b29db847c8d5b8cb9915e80dcf` |

---

## 5. Automated Verification Helper CLI

You can display or verify all parameters using the CLI helper:

```bash
# Display verification parameters for Polygon
python scripts/verify_contracts.py --chain polygon

# Display verification parameters for Base & Arbitrum
python scripts/verify_contracts.py --chain base
python scripts/verify_contracts.py --chain arbitrum

# Display all chains
python scripts/verify_contracts.py --chain all
```
