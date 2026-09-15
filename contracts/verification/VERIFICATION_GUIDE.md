# Smart Contract Verification & Public Explorer Guide

This guide provides everything required to verify and publicly display the **Agent Security Gate x402** contracts on block explorers (**Polygonscan**, **BaseScan**, **Arbiscan**).

---

## 1. Quick Verification Parameters

| Parameter | Value |
| :--- | :--- |
| **Solidity Compiler Version** | `v0.8.20+commit.a1b79de6` |
| **Open Source License Type** | `MIT License (MIT)` |
| **Optimization** | `No` (최적화 안 함 / False) |
| **EVM Version** | `default` |

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

* **Deployed Address**: [`0x4f115665a2BdE534bb7fC426e89ca0BfE2De3B50`](https://polygonscan.com/address/0x4f115665a2BdE534bb7fC426e89ca0BfE2De3B50#code)
* **Direct Verification URL**: [https://polygonscan.com/verifyContract?a=0x4f115665a2BdE534bb7fC426e89ca0BfE2De3B50](https://polygonscan.com/verifyContract?a=0x4f115665a2BdE534bb7fC426e89ca0BfE2De3B50)
* **Source File**: [`contracts/verification/AgentInsurancePool.flattened.sol`](AgentInsurancePool.flattened.sol)
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

* **Deployed Address**: [`0xd0Aa4Aed2AeDE14611B53C3e93CF784F3Fe05BB0`](https://polygonscan.com/address/0xd0Aa4Aed2AeDE14611B53C3e93CF784F3Fe05BB0#code)
* **Direct Verification URL**: [https://polygonscan.com/verifyContract?a=0xd0Aa4Aed2AeDE14611B53C3e93CF784F3Fe05BB0](https://polygonscan.com/verifyContract?a=0xd0Aa4Aed2AeDE14611B53C3e93CF784F3Fe05BB0)
* **Source File**: [`contracts/verification/AgentFactoringPool.flattened.sol`](AgentFactoringPool.flattened.sol)
* **Constructor Arguments**: Same as Insurance Pool
* **ABI-Encoded Constructor Arguments (HEX)**:

```text
0000000000000000000000003c499c542cef5e3811e1192ce70d8cc03d5c3359000000000000000000000000255f9991233f86b29db847c8d5b8cb9915e80dcf000000000000000000000000255f9991233f86b29db847c8d5b8cb9915e80dcf
```

---

### Contract 8: `AgentTreasuryVault.sol` (Hedge Fund & Treasury Vault)

* **Deployed Address**: [`0xfCf3BF5fB5858db9aE81bE458B39b0032fc0C638`](https://polygonscan.com/address/0xfCf3BF5fB5858db9aE81bE458B39b0032fc0C638#code)
* **Direct Verification URL**: [https://polygonscan.com/verifyContract?a=0xfCf3BF5fB5858db9aE81bE458B39b0032fc0C638](https://polygonscan.com/verifyContract?a=0xfCf3BF5fB5858db9aE81bE458B39b0032fc0C638)
* **Source File**: [`contracts/verification/AgentTreasuryVault.flattened.sol`](AgentTreasuryVault.flattened.sol)
* **Constructor Arguments**: Same as Insurance Pool
* **ABI-Encoded Constructor Arguments (HEX)**:

```text
0000000000000000000000003c499c542cef5e3811e1192ce70d8cc03d5c3359000000000000000000000000255f9991233f86b29db847c8d5b8cb9915e80dcf000000000000000000000000255f9991233f86b29db847c8d5b8cb9915e80dcf
```

---

### Contract 9: `SecurityGateConsumer.sol` (End-to-End Showcase Consumer)

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

## 3. Automated Verification Helper CLI

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
