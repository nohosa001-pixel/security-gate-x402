# 🛡️ Safe{Wallet} App Submission & Outreach Package

이 문서는 Safe 공식 팀(Discord, GitHub, Ecosystem Leads)에 전달할 **공식 등록 신청서 및 커뮤니케이션 패키지**입니다.

> ⚠️ **중요 현황 공유**:  
> 현재 Safe 공식 팀은 `safe-global/safe-apps-list` 레포지토리의 자동 PR 접수를 일시 중단(Paused)하고 신청 프로세스를 전면 개편 중입니다.  
> 따라서 현재 신규 Safe App들은 **(1) Discord 개발자 직통 채널** 또는 **(2) Safe Grants/Partnership 팀**과의 직접 소통을 통해 우선 검토를 받고 있습니다.

---

## 💬 1. Safe 공식 디스코드 (Discord) 투척용 메시지 (복사/붙여넣기용)

- **디스코드 서버**: [Safe Official Discord](https://discord.gg/safeglobal)
- **추천 채널**: `#dev-chat`, `#safe-apps`, 또는 `#general-dev`

```markdown
Hey Safe Ecosystem Team! 👋

We built **SafeSecurityGateGuard**, an open-source `ITransactionGuard` designed to protect Safe multisigs and DAO treasuries from autonomous AI agent exploits, prompt injections, and rogue execution loops.

👉 **Key Highlights:**
1. **Consensus-level Defense ("No Proof-of-Safety, No Execution")**: The Safe reverts on-chain unless transactions carry a valid EIP-712 cryptographic attestation with `riskScore <= 30` from our <5ms micro-oracle.
2. **Safe App Ready**: Fully configured with Safe manifest and CSP headers, already tested as a Custom App across Polygon, Base, Arbitrum, and Ethereum.
3. **Open-Source**: Contracts, SDK, and audit proofs are fully public.

- **Hosted App**: https://agent-security-gate-x402-212942243360.asia-northeast3.run.app
- **Manifest**: https://agent-security-gate-x402-212942243360.asia-northeast3.run.app/manifest.json
- **GitHub**: https://github.com/nohosa001-pixel/security-gate-x402
- **Guard Contract**: https://github.com/nohosa001-pixel/security-gate-x402/blob/main/contracts/SafeSecurityGateGuard.sol

Since the `safe-apps-list` PR process is currently being reworked, who from the Ecosystem/App review team can we coordinate with to list this in the default Safe Apps directory? Thank you! 🙏
```

---

## 📋 2. 공식 GitHub / Pre-assessment 신청서 데이터 (JSON & Markdown)

Safe 팀이 폼이나 GitHub에서 요구하는 표준 메타데이터 양식입니다.

### [앱 메타데이터 요약]
* **App Name**: `Agent Security Gate x402`
* **Short Description** (200자 제한 준수): `Deterministic AI Agent Treasury Guard & Autonomous Transaction Micro-Oracle for Safe{Core}. Protects DAO multisigs against prompt injections and budget drains.`
* **App URL**: `https://agent-security-gate-x402-212942243360.asia-northeast3.run.app`
* **Icon URL**: `https://agent-security-gate-x402-212942243360.asia-northeast3.run.app/safe-icon.svg`
* **Supported Chains**:
  * `1` (Ethereum Mainnet)
  * `137` (Polygon PoS)
  * `8453` (Base)
  * `42161` (Arbitrum One)
* **Category**: `Security / AI / Infrastructure`
* **Tags**: `["security", "ai-agents", "oracle", "guard", "defi"]`
* **GitHub Repository**: `https://github.com/nohosa001-pixel/security-gate-x402`
* **Smart Contract (Guard)**: `contracts/SafeSecurityGateGuard.sol`
* **License**: `MIT`

---

## ✉️ 3. Safe 파트너십 / 지원팀 이메일 문의 템플릿

- **받는 사람**: `dev@safe.global` 또는 `ecosystem@safe.global`
- **제목**: `[Safe App Listing Request] Agent Security Gate x402 (AI Agent Treasury Defense Guard)`

```text
Dear Safe Ecosystem Team,

We would like to introduce and list our Safe App: "Agent Security Gate x402".

With the rapid adoption of autonomous AI agents (ElizaOS, LangChain, CrewAI) executing on-chain transactions, Safe treasuries face critical risks from prompt injections and uncontrolled tool-calling loops.

To solve this, we implemented SafeSecurityGateGuard (an open-source ITransactionGuard):
- Enforces "No Proof-of-Safety, No Execution" at the EVM consensus layer.
- Transactions are checked against an ultra-fast (<5ms) micro-oracle that signs EIP-712 attestations only if the risk score is <= 30.
- Reverts any un-attested or malicious transaction before execution.

The app is fully functional and can be loaded via the Custom App feature at:
https://agent-security-gate-x402-212942243360.asia-northeast3.run.app

- Manifest: https://agent-security-gate-x402-212942243360.asia-northeast3.run.app/manifest.json
- Open Source Repo: https://github.com/nohosa001-pixel/security-gate-x402
- Documentation: https://github.com/nohosa001-pixel/security-gate-x402/blob/main/marketing/SAFE_APP_INTEGRATION_GUIDE.md

Please let us know how we can proceed with inclusion in the official default Safe Apps directory.

Best regards,
Agent Security Gate Team
```
