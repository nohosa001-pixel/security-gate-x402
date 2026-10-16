// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC20/extensions/ERC4626.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/utils/cryptography/EIP712.sol";
import "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title Security-Gate-x402 Agentic Shield Insurance Pool (ERC-4626)
 * @notice Accumulates 20% of x402 protocol fees and autonomously indemnifies verified agent exploits
 */

interface ISecurityGateVerifierState {
    function usedNonces(bytes32 nonce) external view returns (bool);
    function gateSigner() external view returns (address);
}

contract AgenticShieldPool is ERC4626, EIP712, ReentrancyGuard, Ownable {
    using SafeERC20 for IERC20;
    using ECDSA for bytes32;

    // ========================================================================
    // 1. 데이터 구조 및 EIP-712 타입 정의
    // ========================================================================

    enum ExploitCategory {
        AST_SANDBOX_BYPASS,       // 0: 결정론적 AST 필터 우회로 인한 악성 코드 실행
        DLP_SECRET_LEAK,          // 1: DLP/ZK-Proxy 결함으로 인한 자격증명 유출
        BOUNDED_CAP_BREACH,       // 2: Safe Guard 한도 초과 오작동
        CORRUPTED_ORACLE_PAYLOAD  // 3: 검증된 오라클 노드의 악성 페이로드 반환
    }

    struct ExploitClaimVerdict {
        bytes32 claimId;            // 고유 청구 ID (keccak256(agentSafe, exploitedTxHash))
        address agentSafe;          // 피해를 입은 에이전트의 Safe{Wallet} 주소
        bytes32 exploitedTxHash;    // 해킹이 발생한 온체인 트랜잭션 해시
        bytes32 attestationNonce;   // 사고 당시 SecurityGate가 발급했던 SafetyAttestation Nonce
        uint256 verifiedLossUsdc;   // 온체인 포렌식으로 확인된 실제 USDC 손실액 (6 decimals)
        ExploitCategory category;   // 사고 유형 분류
        uint64 incidentTimestamp;   // 사고 발생 시각
        uint64 verdictExpiry;       // 배상 판정서 서명 만료 시각
    }

    bytes32 public constant EXPLOIT_VERDICT_TYPEHASH = keccak256(
        "ExploitClaimVerdict(bytes32 claimId,address agentSafe,bytes32 exploitedTxHash,bytes32 attestationNonce,uint256 verifiedLossUsdc,uint8 category,uint64 incidentTimestamp,uint64 verdictExpiry)"
    );

    // ========================================================================
    // 2. 상태 변수 및 리스크 파라미터 (Actuarial Guardrails)
    // ========================================================================

    ISecurityGateVerifierState public immutable gateRouter;
    ISecurityGateVerifierState public immutable safeGuard;

    // 자동 포렌식 검증기(Forensic Oracle Node) 서명자 주소
    address public forensicVerifierSigner;

    // 배상 한도 설정 (USDC 6 decimals 기준)
    uint256 public maxPayoutPerIncident = 10_000 * 1e6; // 건당 최대 $10,000 USDC 배상
    uint256 public maxPoolDrainBps = 1000;              // 단일 배상이 전체 풀 TVL의 10%를 넘지 못함
    uint256 public claimCooldownPeriod = 7 days;        // 동일 에이전트 지갑의 연속 청구 제한 주기

    // 상태 추적 매핑
    mapping(bytes32 => bool) public settledClaims;            // claimId 중복 배상 방지
    mapping(bytes32 => bool) public indemnifiedNonces;        // 동일 Attestation Nonce 재청구 방지
    mapping(address => uint256) public lastClaimTimestamp;    // 에이전트별 최근 배상 시각
    mapping(address => uint256) public totalIndemnifiedByAgent;

    uint256 public totalClaimsPaidUsdc;
    uint256 public totalIncidentsResolved;

    // ========================================================================
    // 3. 이벤트 및 커스텀 에러
    // ========================================================================

    event AutonomousPayoutExecuted(
        bytes32 indexed claimId,
        address indexed agentSafe,
        bytes32 indexed attestationNonce,
        uint256 verifiedLoss,
        uint256 actualPayout,
        ExploitCategory category
    );

    event ForensicSignerUpdated(address indexed oldSigner, address indexed newSigner);
    event RiskParametersUpdated(uint256 maxPerIncident, uint256 maxDrainBps, uint256 cooldown);

    error ClaimAlreadySettled();
    error VerdictSignatureExpired();
    error InvalidForensicSignature();
    error AttestationNeverExecutedOnChain(bytes32 nonce);
    error AgentInCooldownPeriod(uint256 availableAt);
    error ZeroPoolLiquidity();

    constructor(
        IERC20 _usdc,
        address _gateRouter,
        address _safeGuard,
        address _forensicSigner
    )
        ERC20("AGrid Shield LP Vault", "agSHIELD")
        ERC4626(_usdc)
        EIP712("AGridAgenticShield", "1")
        Ownable(msg.sender)
    {
        require(_gateRouter != address(0) && _safeGuard != address(0), "Invalid gate contracts");
        require(_forensicSigner != address(0), "Invalid forensic signer");

        gateRouter = ISecurityGateVerifierState(_gateRouter);
        safeGuard = ISecurityGateVerifierState(_safeGuard);
        forensicVerifierSigner = _forensicSigner;
    }

    // ========================================================================
    // 4. 무신뢰 자동 손실 검증 및 즉시 배상 엔진 (Core Indemnification)
    // ========================================================================

    /**
     * @notice Security Gate를 정상 통과한 트랜잭션에서 보안 사고 발생 시,
     *         온체인 Nonce 기록과 포렌식 EIP-712 서명을 대조해 즉시 에이전트 Safe 지갑으로 USDC 배상
     */
    function claimAutonomousIndemnity(
        ExploitClaimVerdict calldata verdict,
        bytes calldata forensicSignature
    ) external nonReentrant returns (uint256 payoutAmount) {
        // 1. 기본 무결성 및 중복 청구 방어
        if (settledClaims[verdict.claimId] || indemnifiedNonces[verdict.attestationNonce]) {
            revert ClaimAlreadySettled();
        }
        if (block.timestamp > verdict.verdictExpiry) {
            revert VerdictSignatureExpired();
        }
        if (block.timestamp < lastClaimTimestamp[verdict.agentSafe] + claimCooldownPeriod) {
            revert AgentInCooldownPeriod(lastClaimTimestamp[verdict.agentSafe] + claimCooldownPeriod);
        }

        // 2. [핵심] 온체인 교차 검증: 해당 트랜잭션이 실제로 SecurityGateRouter 또는 SafeGuard를 통과했는지 확인
        bool usedInRouter = gateRouter.usedNonces(verdict.attestationNonce);
        bool usedInGuard = safeGuard.usedNonces(verdict.attestationNonce);
        if (!usedInRouter && !usedInGuard) {
            revert AttestationNeverExecutedOnChain(verdict.attestationNonce);
        }

        // 3. 포렌식 오라클 노드의 EIP-712 판정 서명 검증
        bytes32 structHash = keccak256(
            abi.encode(
                EXPLOIT_VERDICT_TYPEHASH,
                verdict.claimId,
                verdict.agentSafe,
                verdict.exploitedTxHash,
                verdict.attestationNonce,
                verdict.verifiedLossUsdc,
                uint8(verdict.category),
                verdict.incidentTimestamp,
                verdict.verdictExpiry
            )
        );

        bytes32 digest = _hashTypedDataV4(structHash);
        if (digest.recover(forensicSignature) != forensicVerifierSigner) {
            revert InvalidForensicSignature();
        }

        // 4. 배상 금액 산출 (실제 손실액, 건당 하드 캡 $10,000, 풀 유동성의 10% 중 최솟값 적용)
        uint256 currentPoolAssets = totalAssets();
        if (currentPoolAssets == 0) revert ZeroPoolLiquidity();

        uint256 maxAllowedFromPool = (currentPoolAssets * maxPoolDrainBps) / 10000;
        payoutAmount = verdict.verifiedLossUsdc;

        if (payoutAmount > maxPayoutPerIncident) {
            payoutAmount = maxPayoutPerIncident;
        }
        if (payoutAmount > maxAllowedFromPool) {
            payoutAmount = maxAllowedFromPool;
        }

        // 5. 상태 업데이트 및 피해 에이전트의 Safe{Wallet}로 즉시 USDC 배상금 송금
        settledClaims[verdict.claimId] = true;
        indemnifiedNonces[verdict.attestationNonce] = true;
        lastClaimTimestamp[verdict.agentSafe] = block.timestamp;
        totalIndemnifiedByAgent[verdict.agentSafe] += payoutAmount;

        totalClaimsPaidUsdc += payoutAmount;
        totalIncidentsResolved += 1;

        IERC20(asset()).safeTransfer(verdict.agentSafe, payoutAmount);

        emit AutonomousPayoutExecuted(
            verdict.claimId,
            verdict.agentSafe,
            verdict.attestationNonce,
            verdict.verifiedLossUsdc,
            payoutAmount,
            verdict.category
        );
    }

    // ========================================================================
    // 5. 실시간 보험료 견적 및 보장 한도 조회 (`quote_agent_insurance` 연동용)
    // ========================================================================

    /**
     * @notice MCP의 `quote_agent_insurance` 툴이 온체인에서 실시간으로 호출하는 뷰 함수
     * @return currentPoolTvl 현재 보험 풀에 쌓인 총 USDC 준비금
     * @return effectiveMaxCoverage 지금 당장 사고 발생 시 즉시 지급 가능한 최대 보장액
     * @return impliedSolvencyRatio 누적 배상액 대비 현재 준비금 건전성 비율 (BPS)
     */
    function getLiveCoverageMetrics()
        external
        view
        returns (
            uint256 currentPoolTvl,
            uint256 effectiveMaxCoverage,
            uint256 impliedSolvencyRatio
        )
    {
        currentPoolTvl = totalAssets();
        uint256 poolCap = (currentPoolTvl * maxPoolDrainBps) / 10000;
        effectiveMaxCoverage = poolCap < maxPayoutPerIncident ? poolCap : maxPayoutPerIncident;

        if (totalClaimsPaidUsdc == 0) {
            impliedSolvencyRatio = 10000; // 100.00% 무사고 상태
        } else {
            impliedSolvencyRatio = (currentPoolTvl * 10000) / (currentPoolTvl + totalClaimsPaidUsdc);
        }
    }

    // ========================================================================
    // 6. 관리자 리스크 파라미터 조정
    // ========================================================================

    function setForensicSigner(address _newSigner) external onlyOwner {
        require(_newSigner != address(0), "Zero address");
        emit ForensicSignerUpdated(forensicVerifierSigner, _newSigner);
        forensicVerifierSigner = _newSigner;
    }

    function updateRiskParameters(
        uint256 _maxPerIncident,
        uint256 _maxDrainBps,
        uint256 _cooldown
    ) external onlyOwner {
        require(_maxDrainBps <= 3000, "Drain cap cannot exceed 30% of pool");
        maxPayoutPerIncident = _maxPerIncident;
        maxPoolDrainBps = _maxDrainBps;
        claimCooldownPeriod = _cooldown;
        emit RiskParametersUpdated(_maxPerIncident, _maxDrainBps, _cooldown);
    }
}
