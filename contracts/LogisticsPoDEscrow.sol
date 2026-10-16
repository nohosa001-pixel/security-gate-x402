// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/utils/cryptography/EIP712.sol";
import "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

/**
 * @title A.GRID Logistics Proof-of-Delivery (PoD) Autonomous Escrow
 * @notice Releases or refunds USDC trade escrows autonomously based on EIP-712 Logistics Oracle attestations
 */
contract LogisticsPoDEscrow is EIP712, ReentrancyGuard {
    using SafeERC20 for IERC20;
    using ECDSA for bytes32;

    struct ProofOfDelivery {
        bytes32 dealId;
        bytes32 blDocumentHash;
        bytes32 containerIdHash;
        uint32 vesselImo;
        bytes5 unlocodeDestination;
        bytes32 telemetryMerkleRoot;
        uint64 deliveryTimestamp;
        bool conditionPassed;
    }

    bytes32 public constant POD_TYPEHASH = keccak256(
        "ProofOfDelivery(bytes32 dealId,bytes32 blDocumentHash,bytes32 containerIdHash,uint32 vesselImo,bytes5 unlocodeDestination,bytes32 telemetryMerkleRoot,uint64 deliveryTimestamp,bool conditionPassed)"
    );

    struct FreightEscrow {
        address buyerAgent;
        address sellerExporter;
        uint256 usdcAmount;
        bytes32 expectedBlHash;
        bytes32 expectedContainerHash;
        bytes5 requiredDestPort;
        bool isSecurityGateGuarded; // Security Gate 통과 시 수수료 0.5%, 미통과 시 1.5%
        bool settled;
    }

    IERC20 public immutable usdc;
    address public logisticsOracleSigner;
    address public protocolFeeSplitter; // 70:20:10 분배 라우터

    uint256 public constant GUARDED_FEE_BPS = 50;     // 0.5%
    uint256 public constant UNVERIFIED_FEE_BPS = 150; // 1.5%

    mapping(bytes32 => FreightEscrow) public freightDeals;

    event FreightEscrowLocked(
        bytes32 indexed dealId,
        address indexed buyer,
        address indexed seller,
        uint256 amount,
        bytes32 expectedBlHash,
        bytes5 destPort
    );

    event ProofOfDeliverySettled(
        bytes32 indexed dealId,
        address indexed recipient,
        uint256 netPayout,
        bytes32 telemetryMerkleRoot,
        bool slaPassed
    );

    error InvalidLogisticsSignature();
    error BillOfLadingMismatch();
    error ContainerHashMismatch();
    error DestinationPortMismatch();
    error DealAlreadySettled();

    constructor(
        address _usdc,
        address _logisticsOracleSigner,
        address _protocolFeeSplitter
    ) EIP712("AGridLogisticsOracle", "1") {
        usdc = IERC20(_usdc);
        logisticsOracleSigner = _logisticsOracleSigner;
        protocolFeeSplitter = _protocolFeeSplitter;
    }

    /**
     * @notice 1. 구매 에이전트가 선하증권(eBL) 해시와 목적지 항만 코드를 조건으로 USDC 예치
     */
    function createFreightEscrow(
        bytes32 dealId,
        address sellerExporter,
        uint256 amount,
        bytes32 expectedBlHash,
        bytes32 expectedContainerHash,
        bytes5 requiredDestPort,
        bool isGuardedBySecurityGate
    ) external nonReentrant {
        require(freightDeals[dealId].buyerAgent == address(0), "Deal ID exists");

        usdc.safeTransferFrom(msg.sender, address(this), amount);

        freightDeals[dealId] = FreightEscrow({
            buyerAgent: msg.sender,
            sellerExporter: sellerExporter,
            usdcAmount: amount,
            expectedBlHash: expectedBlHash,
            expectedContainerHash: expectedContainerHash,
            requiredDestPort: requiredDestPort,
            isSecurityGateGuarded: isGuardedBySecurityGate,
            settled: false
        });

        emit FreightEscrowLocked(dealId, msg.sender, sellerExporter, amount, expectedBlHash, requiredDestPort);
    }

    /**
     * @notice 2. 물류 오라클의 EIP-712 Proof-of-Delivery 서명 제출 시 즉시 대금 정산 또는 SLA 위반 환불
     * @dev 구매자, 판매자, 또는 릴레이어 에이전트 누구나 서명만 있으면 호출 가능 (무신뢰 자동 집행)
     */
    function settleWithProofOfDelivery(
        ProofOfDelivery calldata pod,
        bytes calldata oracleSignature
    ) external nonReentrant {
        FreightEscrow storage deal = freightDeals[pod.dealId];
        if (deal.settled) revert DealAlreadySettled();

        // 1. 계약 당시 약정한 선하증권(eBL), 컨테이너, 목적지 항만과 일치하는지 온체인 대조
        if (pod.blDocumentHash != deal.expectedBlHash) revert BillOfLadingMismatch();
        if (pod.containerIdHash != deal.expectedContainerHash) revert ContainerHashMismatch();
        if (pod.unlocodeDestination != deal.requiredDestPort) revert DestinationPortMismatch();

        // 2. 물류 오라클 EIP-712 서명 검증
        bytes32 structHash = keccak256(
            abi.encode(
                POD_TYPEHASH,
                pod.dealId,
                pod.blDocumentHash,
                pod.containerIdHash,
                pod.vesselImo,
                pod.unlocodeDestination,
                pod.telemetryMerkleRoot,
                pod.deliveryTimestamp,
                pod.conditionPassed
            )
        );

        bytes32 digest = _hashTypedDataV4(structHash);
        if (digest.recover(oracleSignature) != logisticsOracleSigner) {
            revert InvalidLogisticsSignature();
        }

        deal.settled = true;

        // 3. Security Gate 통과 여부에 따른 수수료 차감 (0.5% vs 1.5%)
        uint256 feeBps = deal.isSecurityGateGuarded ? GUARDED_FEE_BPS : UNVERIFIED_FEE_BPS;
        uint256 protocolFee = (deal.usdcAmount * feeBps) / 10000;
        uint256 netAmount = deal.usdcAmount - protocolFee;

        // 수수료는 70:20:10 분배 라우터로 전송
        if (protocolFee > 0) {
            usdc.safeTransfer(protocolFeeSplitter, protocolFee);
        }

        // 4. 화물 상태(conditionPassed)가 정상이면 판매자에게 지급, 파손/온도 이탈 시 구매자에게 즉시 환불
        address finalRecipient = pod.conditionPassed ? deal.sellerExporter : deal.buyerAgent;
        usdc.safeTransfer(finalRecipient, netAmount);

        emit ProofOfDeliverySettled(
            pod.dealId,
            finalRecipient,
            netAmount,
            pod.telemetryMerkleRoot,
            pod.conditionPassed
        );
    }
}
