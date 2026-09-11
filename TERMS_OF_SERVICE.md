# Terms of Service & Legal Disclaimer
## Canonical Identifier: `ZERO_LIABILITY_AS_IS_PROVENANCE_V1`

**Last Updated & Effective Date:** September 10, 2026  
**Applicable System:** Agent Security Gate x402 (`agent-security-gate-x402`), Sheriff Micro-Oracle, `SecurityGateConsumer.sol`, and downstream SDKs/APIs.

---

## 1. Acceptance of Terms & Machine-to-Machine (M2M) Binding

By accessing, querying, integrating with, or receiving cryptographic attestations (`AuditAttestation`, `AuditProof`) from **Agent Security Gate x402** (the "Service" or "Oracle"), you—whether an individual, a legal entity, or a software system/autonomous agent acting on behalf of a principal (the "User")—expressly agree to be bound by this Terms of Service agreement (`ZERO_LIABILITY_AS_IS_PROVENANCE_V1`).

If an autonomous agent or bot programmatically interacts with this Service, the owner, deployer, and private key holder of that agent assume full legal and operational responsibility for the agent's actions and are deemed to have assented to these terms upon initiation of any HTTP, RPC, or smart contract call.

---

## 2. Scope & Nature of the Security Gate Oracle

1. **Heuristic & Deterministic Evaluation Only:**  
   The Service evaluates payloads using deterministic regex matching, static Abstract Syntax Tree (AST) scanning, and heuristic Natural Language Inference (NLI) scoring.
2. **No Guarantee of 100% Detection:**  
   The User acknowledges that prompt injection, adversarial evasion, LLM jailbreaking, and smart contract exploit vectors evolve continuously. The Service **DOES NOT** guarantee or warrant that all threats, malicious payloads, fabricated assertions, or zero-day vulnerabilities will be intercepted.
3. **No Financial or Investment Advice:**  
   Verdicts (`PASSED`, `FLAGGED`, `BLOCKED`) and risk scores (0–100) are automated technical classifications. Under no circumstances do they constitute financial advice, investment counsel, solvency endorsements, or auditing certifications for any token, wallet, agent, or smart contract.

---

## 3. "AS IS" & Express Disclaimer of Warranties

TO THE MAXIMUM EXTENT PERMITTED BY APPLICABLE LAW:
* THE SERVICE, ITS SMART CONTRACTS (`SecurityGateConsumer.sol`, `SafeSecurityGateGuard.sol`), ORACLE SIGNATURES, AND ATTESTATIONS ARE PROVIDED STRICTLY ON AN **"AS IS"** AND **"AS AVAILABLE"** BASIS.
* THE OPERATORS, DEVELOPERS, AND CONTRIBUTORS EXPRESSLY DISCLAIM ALL WARRANTIES OF ANY KIND, WHETHER EXPRESS, IMPLIED, STATUTORY, OR OTHERWISE, INCLUDING BUT NOT LIMITED TO THE IMPLIED WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, TITLE, AND NON-INFRINGEMENT.
* NO ORAL OR WRITTEN STATEMENT OR VERDICT ISSUED BY THE ORACLE SHALL CREATE ANY WARRANTY NOT EXPRESSLY STATED HEREIN.

---

## 4. Limitation of Liability

TO THE MAXIMUM EXTENT PERMITTED UNDER APPLICABLE LAW, IN NO EVENT SHALL THE SERVICE OPERATORS, DEVELOPERS, SIGNERS, CONTRIBUTORS, OR AFFILIATES BE LIABLE FOR:
1. **Any Indirect, Special, Consequential, or Punitive Damages:**  
   Including loss of profits, revenue, data, digital assets, tokens, gas fees, or business opportunities arising out of or in connection with the use or inability to use the Service.
2. **Exploits, Slippage, or Liquidation Events:**  
   Any loss resulting from downstream execution of agent transactions, unexpected slippage, smart contract bugs in consumer contracts, or unauthorized transactions executed despite an oracle `PASSED` attestation.
3. **Blockchain Network Failures:**  
   Chain reorganizations, hard forks, RPC outages, gas spikes, network latency, or validator censorship on Polygon, Base, Arbitrum, Ethereum, or any other settlement layer.

### Cumulative Liability Cap
IN ANY EVENT, THE TOTAL AGGREGATE LIABILITY OF THE SERVICE OPERATORS ARISING OUT OF OR RELATED TO THIS SERVICE SHALL NOT EXCEED THE GREATER OF:
- **FIFTY UNITED STATES DOLLARS ($50.00 USD)**, OR
- **THE TOTAL FEES (IN USDC) ACTUALLY PAID BY THE USER TO THE SERVICE IN THE THIRTY (30) DAYS IMMEDIATELY PRECEDING THE EVENT GIVING RISE TO LIABILITY.**

---

## 5. Blockchain Finality & Autonomous Execution Assumption of Risk

1. **Non-Reversibility:**  
   The User acknowledges that blockchain transactions are irreversible. Once an on-chain action is authorized or executed via `SecurityGateConsumer.sol` or `BoundedAgentWallet`, funds cannot be retrieved, recalled, or reversed by the Oracle or its operators.
2. **Client-Side Final Authority:**  
   The Service serves solely as an informational security layer. The final authorization and dispatch of cryptographic private key signatures remain strictly under the control and responsibility of the client application and agent wallet.

---

## 6. Cryptographic Provenance & Proof Verification

When an `AuditProof` or `AuditAttestation` is signed by the Sheriff oracle private key, the signature embeds:
* `terms`: `"ZERO_LIABILITY_AS_IS_PROVENANCE_V1"`
* `proof_hash`: A deterministic SHA-256 fingerprint of the audit metadata.

The cryptographic verification of this signature constitutes prima facie evidence that the recipient accepted the provenance and the associated limitation of liability provisions embedded herein.

---

## 7. Governing Law & Dispute Resolution

To the fullest extent permissible by law, these Terms shall be governed by and construed in accordance with general principles of international commercial arbitration and the laws of the jurisdiction of the project's principal operating entity, without regard to conflict of law principles. Any dispute arising under this agreement shall be resolved through binding arbitration.

---

## 8. Modifications & Inquiries

The canonical version of this document is maintained at:
- Endpoint: `GET /api/v1/terms`
- Repository: [TERMS_OF_SERVICE.md](https://github.com/nohosa001-pixel/security-gate-x402/blob/main/TERMS_OF_SERVICE.md)
- Canonical SHA-256 Fingerprint: Published and verifiable via `/api/v1/terms`

Inquiries regarding institutional agreements or custom SLAs should be directed to `security@agent-finance.org`.
