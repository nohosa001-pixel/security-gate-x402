# 🏛️ A.GRID | Week 2 Build Log (Phase 2: Institutional Compliance & Bypass Defense)

> **Track**: Agentic Security / Real-World Trade Oracles / x402 Settlement  
> **Live Solana Mainnet Programs**: `AGR3W3R9pKxnuZGYrpaggfkbMKVrjoniLaGvi1voBFSC` · `AGRAtNxF474xZFin5iZaxBKE2fKNKPih7qYPEm3mu9oN`  
> **Polygon Mainnet Policy (`SecurityGateOMSPolicy.sol`)**: `0x4A28F9A2E6D0DcB69791980560FC8364A514f205`  
> **Live Hub**: [https://agent-security-gate-x402-212942243360.asia-northeast3.run.app/hub/](https://agent-security-gate-x402-212942243360.asia-northeast3.run.app/hub/)  
> **Week 2 Demo Video**: [https://youtube.com/shorts/SB_bzork6jg](https://youtube.com/shorts/SB_bzork6jg)

---

## 🎯 Phase 2 Focus: Closing Real-World Attack Vectors & EU Regulatory Readiness

In Week 1, we established our `<2.8ms` deterministic AST Pre-Sign Guard and Solana PDA spend caps.  
In **Week 2 (Phase 2)**, we expanded from single-tx blocking to **full institutional execution safety**:

1. **Closing ERC-20 `approve` / `permit` Drain Bypasses (`SecurityGateOMSPolicy.sol`)**
   - Most naive session-key policies only check native `value` or direct `transfer`. Attackers bypass them by tricking an agent into calling `approve()`, `increaseAllowance()`, or EIP-2612 `permit()`.
   - `checkUserOpPolicy` now decodes `ERC20_TRANSFER_SEL`, `ERC20_APPROVE_SEL`, `ERC20_INCREASE_ALLOWANCE_SEL`, `ERC20_TRANSFER_FROM_SEL`, and `EIP2612_PERMIT_SEL` directly on-chain, enforcing `allowedTarget` whitelisting on `spender`/`recipient` and counting approved allowances toward the cumulative `maxSpendLimit`.
   - Every execution additionally requires a short-lived **EIP-712 Security Gate Attestation** (`riskScore`, `verdict`, `expiry`, signature).

2. **Dual-Mode Statutory Governance (`GDPR Art. 17(1)` vs. `Art. 17(3)(b)`)**
   - **Mode A (5-Year Statutory Audit Lock — `1,825 Days`)**: For `EUDR` (EU Deforestation Regulation), `MINERALS` (OECD 3TG), `TRADE` (e-B/L), and `CONSTRUCTION`, compliance artifacts are locked in an immutable audit vault while ephemeral PII is zeroized in `0s` (`NIST-SP-800-88-Rev1`).
   - **Mode B (0s Immediate Trade-Secret Purge)**: For `BIO`, `M2M`, and `CLEANWEB`, raw payloads are purged in `0s`, leaving only the `O(1)` cryptographic receipt hash on-chain.
   - **Mode C (`IFRS-15 / US GAAP` Enterprise Clean Invoice)**: Enforces `0%` (`$0.00`) kickbacks/rebates on all Enterprise B2B settlements for FCPA / UK Bribery Act compliance.

3. **Autonomous Continuous Threat Brain (`scripts/run_continuous_brain_trainer.py`)**
   - Continuous daemon expanding our proprietary injection, jailbreak, and payload-evasion defense corpus without relying on external LLM calls at runtime.

---

## 📹 Week 2 Demo Video Script (60~75 Seconds)

| Time | Visual on Screen | Voiceover / Narrative |
| :--- | :--- | :--- |
| **00:00 - 00:15** | Split screen: `SecurityGateOMSPolicy.sol` (`checkUserOpPolicy`) + Terminal running bypass simulation. | *"In Week 2, we closed one of the sneakiest agent wallet drains: ERC-20 `approve` and EIP-2612 `permit` bypasses. Even if an LLM is tricked into approving an attacker's spender address, our on-chain policy decodes the calldata and reverts immediately."* |
| **00:15 - 00:35** | Live API / Hub dashboard showing EUDR & Trade Escrow settlement + `IFRS-15` Clean Invoice JSON. | *"Second, with European trade regulations like EUDR hitting full enforcement, enterprises can't use leaky crypto rails. A.GRID enforces Dual-Mode Governance: 0-second PII zeroization under NIST 800-88, paired with a 5-year statutory audit lock and zero-kickback IFRS-15 clean invoices."* |
| **00:35 - 00:55** | Terminal showing `run_continuous_brain_trainer.py` running + `<5ms` audit verdict. | *"Under the hood, our continuous threat trainer hardens our deterministic `<5ms` AST firewall around the clock—no external LLM latency, no blind trust."* |
| **00:55 - 01:10** | Live Hub URL & Solana Mainnet Program IDs (`AGR3W3R9...`, `AGRAtNxF...`). | *"Live today on Solana Mainnet. Independent policy enforcement, deterministic truth oracles, and enterprise compliance in one clearinghouse. We are A.GRID. Thank you."* |

---

## 🗣️ Week 2 Video Pronunciation Guide (촬영용 대본)

1. **Scene 1 (0:00~0:15)**
   > "In Week 2, we closed one of the sneakiest agent wallet drains: ERC-20 approve and EIP-2612 permit bypasses. Even if an LLM is tricked into approving an attacker's spender address, our on-chain policy decodes the calldata and reverts immediately."
   * 발음: "인 위크 투, 위 클로즈드 원 오브 더 스니키스트 에이전트 월렛 드레인즈: 이알씨-트웬티 어프루브 앤드 이아이피-트웬티식스투웰브 퍼밋 바이패시스. 이븐 이프 언 엘엘엠 이즈 트릭드 인투 어프루빙 언 어태커스 스펜더 어드레스, 아워 온-체인 폴리시 디코즈 더 콜데이터 앤드 리버츠 이미디어틀리."

2. **Scene 2 (0:15~0:35)**
   > "Second, with European trade rules like EUDR hitting full enforcement, enterprises can't use leaky crypto rails. A.GRID enforces Dual-Mode Governance: zero-second PII zeroization under NIST 800-88, paired with a 5-year statutory audit lock and zero-kickback IFRS-15 clean invoices."
   * 발음: "세컨드, 위드 유러피언 트레이드 룰즈 라이크 이유디알 히팅 풀 인포스먼트, 엔터프라이지즈 캔트 유즈 리키 크립토 레일즈. 에이그리드 인포시즈 듀얼-모드 거버넌스: 제로-세컨드 피아이아이 제로이제이션 언더 니스트 에잇헌드레드-에이티에잇, 페어드 위드 어 파이브-이어 스타튜토리 오딧 락 앤드 제로-킥백 아이에프알에스-피프틴 클린 인보이시스."

3. **Scene 3 (0:35~0:55)**
   > "Under the hood, our continuous threat trainer hardens our deterministic sub-five-millisecond AST firewall around the clock—no external LLM latency, no blind trust."
   * 발음: "언더 더 후드, 아워 컨티뉴어스 쓰렛 트레이너 하든즈 아워 디터미니스틱 서브-파이브-밀리세컨드 에이에스티 파이어월 어라운드 더 클락—노 익스터널 엘엘엠 레이턴시, 노 블라인드 트러스트."

4. **Scene 4 (0:55~01:10)**
   > "Live today on Solana Mainnet. Independent policy enforcement, deterministic truth oracles, and enterprise compliance in one clearinghouse. We are A.GRID. Thank you."
   * 발음: "라이브 투데이 온 솔라나 메인넷. 인디펜던트 폴리시 인포스먼트, 디터미니스틱 트루스 오라클즈, 앤드 엔터프라이즈 컴플라이언스 인 원 클리어링하우스. 위 아 에이그리드. 땡큐."

---

## 📣 Reddit (`r/ethdev` / `r/solana`) Week 2 Update Post Draft

**Title:**
`[Week 2 Update] Hardening AI Agent Spend Policies Against ERC-20 approve()/permit() Bypasses + EU Regulatory Audit Locks (Solana & Polygon)`

**Body:**
```markdown
Last week we shared our `<2.8ms` deterministic AST Pre-Sign Guard and on-chain spend caps for autonomous AI agents. Here is what we shipped in **Week 2** to close real-world bypasses and prepare for enterprise trade compliance:

1. **Closing ERC-20 `approve()` / `permit()` Drain Bypasses (`SecurityGateOMSPolicy.sol`)**
   - A naive per-tx native value cap is easy to bypass if a prompt-injected agent calls `approve()`, `increaseAllowance()`, or EIP-2612 `permit()` to hand an attacker's address unlimited allowance.
   - Our `checkUserOpPolicy` now decodes those calldata selectors directly on-chain, enforces `allowedTarget` whitelisting on the `spender`/`recipient`, adds approved allowances to the cumulative `maxSpendLimit`, and verifies a short-lived EIP-712 Security Gate attestation (`riskScore`, `verdict`, `expiry`).

2. **Dual-Mode Statutory Governance (GDPR vs. EU Trade Audits)**
   - **Mode A (5-Year / 1,825-Day Statutory Audit Lock):** For EUDR (deforestation), conflict minerals (OECD 3TG), and maritime e-B/L settlements, compliance payloads are anchored immutably while ephemeral PII is zeroized in `0s` (`NIST-SP-800-88-Rev1`).
   - **Mode C (`IFRS-15 / US GAAP` Clean Invoicing):** Enforces `0%` (`$0.00`) kickbacks/rebates on enterprise B2B settlements.

3. **Continuous Threat Brain (`run_continuous_brain_trainer.py`)**
   - Background adversarial training loop continuously hardening our deterministic `<5ms` AST & prompt-injection inspection without runtime LLM latency.

Live Hub: https://agent-security-gate-x402-212942243360.asia-northeast3.run.app/hub/
Polygon Verified Policy: `0x4A28F9A2E6D0DcB69791980560FC8364A514f205`
Solana Mainnet Programs: `AGR3W3R9pKxnuZGYrpaggfkbMKVrjoniLaGvi1voBFSC` / `AGRAtNxF474xZFin5iZaxBKE2fKNKPih7qYPEm3mu9oN`

Would love feedback from smart contract & agent security engineers—especially on cross-wallet velocity limits and oracle-normalized caps for volatile assets!
```
