# 🧙‍♂️ Ethereum Magicians Proposal Draft

> **Target Site**: [Fellowship of Ethereum Magicians](https://ethereum-magicians.org/)  
> **Category**: **ERC / Standards**  
> **Topic Title**: `ERC: AI Agent Proof-of-Safety Attestation & Transaction Guard Standard (IAgentTransactionGuard)`

---

## 📌 Post Content (Copy & Paste to ethereum-magicians.org)

### Title

`ERC: AI Agent Proof-of-Safety Attestation & Transaction Guard Standard (IAgentTransactionGuard)`

### Body

```yaml
eip: <to be assigned>
title: AI Agent Proof-of-Safety Attestation and Transaction Guard Standard
description: Standardized EIP-712 cryptographic safety attestation and execution guard for autonomous AI agent smart contract accounts.
author: Security Gate x402 Architecture Team (@nohosa001-pixel)
discussions-to: https://ethereum-magicians.org/
status: Draft
type: Standards Track
category: ERC
created: 2026-09-13
requires: 712, 1271, 4337
```

### Abstract

This standard specifies an on-chain interface and cryptographic verification flow for autonomous AI agents executing financial transactions via smart contract accounts (such as Gnosis Safe multisigs and ERC-4337 Smart Accounts).

It introduces `IAgentTransactionGuard` and `IAgentCreditOracle`, preventing unauthorized treasury drains, adversarial prompt injection attacks, and hallucinated transaction calls by requiring signed EIP-712 safety attestations before transaction finality.

### Motivation

As autonomous AI agents manage decentralized treasuries, execute high-frequency arbitrage, and interact with DeFi protocols, existing smart contract architectures lack deterministic mechanisms to verify whether an agent's transaction payload has been verified against:

1. **Adversarial prompt injection attacks** (e.g. DAN prompts, indirect instruction hijacking via untrusted inputs).
2. **Systemic hallucinations or arithmetic discrepancies** in transaction calldata.
3. **Budget and velocity limits** (preventing infinite loops from draining agent treasuries in gas or slippage).

By defining an interoperable standard:

- Any autonomous agent runtime (ElizaOS, LangChain, AutoGen, CrewAI) can obtain standardized cryptographic safety attestations before submitting transactions.
- Any smart contract account (Safe, ERC-4337 account) can enforce deterministic verification through standard transaction guards without proprietary vendor lock-in.

### Specification

The standard comprises two core interfaces:

#### 1. `IAgentTransactionGuard`

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface IAgentTransactionGuard {
    struct SecurityAttestation {
        bytes32 payloadHash;
        uint8 riskScore;
        string verdict;
        uint256 expiresAt;
        uint8 v;
        bytes32 r;
        bytes32 s;
    }

    event SafeTransactionGuarded(address indexed safe, address indexed to, uint256 value, uint8 riskScore);

    function checkTransaction(
        address to,
        uint256 value,
        bytes memory data,
        uint8 operation,
        uint256 safeTxGas,
        uint256 baseGas,
        uint256 gasPrice,
        address gasToken,
        address payable refundReceiver,
        bytes memory signatures,
        address msgSender
    ) external;

    function checkAfterExecution(bytes32 txHash, bool success) external;
}
```

#### 2. `IAgentCreditOracle`

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface IAgentCreditOracle {
    struct AgentCreditProfile {
        address agentAddress;
        uint16 creditScore;      // 300 to 850 (Standard FICO Scale)
        uint256 uncollateralizedCreditLimit;
        uint256 totalAuditedVolume;
        uint32 consecutiveSafeTxCount;
        uint256 lastAuditTimestamp;
        bool isBlacklisted;
    }

    event CreditProfileUpdated(address indexed agent, uint16 newScore, uint256 creditLimit);

    function getCreditProfile(address agent) external view returns (AgentCreditProfile memory);
    function verifyProofOfSafety(bytes32 payloadHash, bytes calldata signature) external view returns (bool isValid, uint8 riskScore);
}
```

### Rationale

- **EIP-712 Compatibility**: Struct hashing ensures off-chain security evaluation oracles can sign machine-readable payloads with verifiable domain separation, preventing replay attacks across different chains or smart accounts.
- **Composable with ERC-4337 & Safe**: Matches existing Safe `ITransactionGuard` signatures and can be extended into an ERC-4337 `IPaymaster` or `IAccount` validation module.
- **Latency Consideration**: Verification takes place off-chain (<5ms micro-oracle) and only the cryptographic signature is verified on-chain, keeping EVM execution gas minimal (~25,000 gas).

### Reference Implementation

A fully working, tested reference implementation of `SafeSecurityGateGuard.sol` and the off-chain micro-oracle is available at:
👉 [https://github.com/nohosa001-pixel/security-gate-x402](https://github.com/nohosa001-pixel/security-gate-x402)

### We Welcome Community Feedback

We are seeking input from the Ethereum standards community and Smart Account/Safe builders:

1. Should `SecurityAttestation` include a nonce field for strict sequential transaction ordering, or is `expiresAt` sufficient for micro-batches?
2. How should multi-oracle consensus (threshold signatures) be structured for ultra-high-value treasury movements?
