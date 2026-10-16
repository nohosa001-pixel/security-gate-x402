// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/utils/cryptography/EIP712.sol";
import "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

/**
 * @title Security-Gate-x402 On-Chain Settlement & Safe Guard Suite
 * @notice Autonomous AI Agent Firewall, EIP-712 Attestation Verifier, and Fee Splitter
 */

// ============================================================================
// 1. Interfaces (EIP-3009 USDC & Safe{Wallet} Guard)
// ============================================================================

interface IERC3009 is IERC20 {
    function transferWithAuthorization(
        address from,
        address to,
        uint256 value,
        uint256 validAfter,
        uint256 validBefore,
        bytes32 nonce,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) external;
}

enum EnumOperation {
    Call,
    DelegateCall
}

interface ITransactionGuard {
    function checkTransaction(
        address to,
        uint256 value,
        bytes memory data,
        EnumOperation operation,
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

// ============================================================================
// 2. Shared EIP-712 Verifier Base
// ============================================================================

abstract contract SecurityGateVerifier is EIP712, Ownable {
    using ECDSA for bytes32;

    struct SafetyAttestation {
        bytes32 payloadHash;      // keccak256(execution calldata or target payload)
        address agentWallet;      // Requesting agent Safe address
        address targetAddress;    // Target destination / oracle address
        uint256 maxAllowedSpend;  // Maximum permitted spend (USDC 6 decimals or Wei)
        uint256 expiry;           // Attestation expiry timestamp
        uint8 riskScore;          // 0~100 (AST/DLP risk evaluation score)
        bytes32 nonce;            // Anti-replay unique nonce
    }

    bytes32 public constant SAFETY_ATTESTATION_TYPEHASH = keccak256(
        "SafetyAttestation(bytes32 payloadHash,address agentWallet,address targetAddress,uint256 maxAllowedSpend,uint256 expiry,uint8 riskScore,bytes32 nonce)"
    );

    // Off-chain security-gate-x402 engine signer address
    address public gateSigner;
    // Track used attestation nonces to prevent replay
    mapping(bytes32 => bool) public usedNonces;

    error InvalidGateSignature();
    error AttestationExpired();
    error NonceAlreadyUsed();
    error RiskScoreTooHigh(uint8 score);

    event GateSignerUpdated(address indexed oldSigner, address indexed newSigner);

    constructor(address _initialSigner) 
        EIP712("SecurityGateX402", "1") 
        Ownable(msg.sender) 
    {
        require(_initialSigner != address(0), "Invalid signer");
        gateSigner = _initialSigner;
    }

    function setGateSigner(address _newSigner) external onlyOwner {
        require(_newSigner != address(0), "Invalid signer");
        emit GateSignerUpdated(gateSigner, _newSigner);
        gateSigner = _newSigner;
    }

    function _verifyAttestation(
        SafetyAttestation calldata attestation,
        bytes calldata signature
    ) internal {
        if (block.timestamp > attestation.expiry) revert AttestationExpired();
        if (usedNonces[attestation.nonce]) revert NonceAlreadyUsed();
        if (attestation.riskScore >= 80) revert RiskScoreTooHigh(attestation.riskScore);

        bytes32 structHash = keccak256(
            abi.encode(
                SAFETY_ATTESTATION_TYPEHASH,
                attestation.payloadHash,
                attestation.agentWallet,
                attestation.targetAddress,
                attestation.maxAllowedSpend,
                attestation.expiry,
                attestation.riskScore,
                attestation.nonce
            )
        );

        bytes32 digest = _hashTypedDataV4(structHash);
        address recovered = digest.recover(signature);

        if (recovered != gateSigner) revert InvalidGateSignature();

        usedNonces[attestation.nonce] = true;
    }
}

// ============================================================================
// 3. Universal Escrow & x402 Fee Router (70:20:10 Revenue Split)
// ============================================================================

contract SecurityGateEscrowRouter is SecurityGateVerifier, ReentrancyGuard {
    using SafeERC20 for IERC20;

    IERC3009 public immutable usdc;

    // Protocol revenue destinations (70% Treasury, 20% Insurance Pool, 10% Relayer Gas Tank)
    address public protocolTreasury;
    address public insuranceVault;
    address public relayerGasTank;

    uint256 public constant BPS_DENOMINATOR = 10000;
    uint256 public constant TREASURY_SHARE_BPS = 7000;  // 70%
    uint256 public constant INSURANCE_SHARE_BPS = 2000; // 20%
    uint256 public constant RELAYER_SHARE_BPS = 1000;   // 10%

    // Base fee parameters (USDC 6 decimals)
    uint256 public microTollFee = 2000;           // $0.002 USDC (2,000 units)
    uint256 public guardedTakeRateBps = 50;       // 0.5% with valid Proof-of-Safety
    uint256 public unverifiedTakeRateBps = 150;   // 1.5% without proof (surcharge)

    struct EscrowDeal {
        address buyerAgent;
        address sellerOracle;
        uint256 amount;
        bytes32 expectedDataHash;
        uint256 unlockTime;
        bool isGuarded;
        bool settled;
    }

    mapping(bytes32 => EscrowDeal) public escrows;

    event FeeDistributed(uint256 totalFee, uint256 treasuryAmt, uint256 insuranceAmt, uint256 relayerAmt);
    event X402DirectSettled(address indexed agent, address indexed oracle, uint256 netAmount, uint256 fee);
    event EscrowCreated(bytes32 indexed dealId, address indexed buyer, address indexed seller, uint256 amount, bool isGuarded);
    event EscrowSettled(bytes32 indexed dealId, address indexed seller, uint256 netPayout);

    constructor(
        address _usdc,
        address _gateSigner,
        address _treasury,
        address _insurance,
        address _relayer
    ) SecurityGateVerifier(_gateSigner) {
        usdc = IERC3009(_usdc);
        protocolTreasury = _treasury;
        insuranceVault = _insurance;
        relayerGasTank = _relayer;
    }

    /**
     * @notice [Tier 1 & Direct Oracle Settlement] EIP-3009 gasless settlement with EIP-712 Proof-of-Safety
     */
    function settleX402WithAttestation(
        // EIP-3009 authorization parameters
        uint256 totalPayment,
        uint256 validAfter,
        uint256 validBefore,
        bytes32 authNonce,
        uint8 v, bytes32 r, bytes32 s,
        // Security Gate EIP-712 attestation parameters
        SafetyAttestation calldata attestation,
        bytes calldata gateSignature
    ) external nonReentrant {
        require(totalPayment <= attestation.maxAllowedSpend, "Exceeds bounded wallet cap");

        // 1. Verify Security Gate EIP-712 Attestation
        _verifyAttestation(attestation, gateSignature);

        // 2. Gasless USDC collection from agent wallet via EIP-3009
        usdc.transferWithAuthorization(
            attestation.agentWallet,
            address(this),
            totalPayment,
            validAfter,
            validBefore,
            authNonce,
            v, r, s
        );

        // 3. Calculate fee: base micro-toll ($0.002) + discounted take-rate (0.5%)
        uint256 takeFee = (totalPayment * guardedTakeRateBps) / BPS_DENOMINATOR;
        uint256 totalFee = microTollFee + takeFee;
        require(totalPayment > totalFee, "Payment too small to cover fee");

        uint256 netOraclePayout = totalPayment - totalFee;

        // 4. Split fee 70:20:10 and disburse net payout to oracle
        _splitAndDistributeFee(totalFee);
        IERC20(address(usdc)).safeTransfer(attestation.targetAddress, netOraclePayout);

        emit X402DirectSettled(attestation.agentWallet, attestation.targetAddress, netOraclePayout, totalFee);
    }

    /**
     * @notice [Tier 2 Conditional Escrow] Instant Finality (0s delay) for guarded agents vs 24h challenge for unverified
     */
    function createEscrow(
        bytes32 dealId,
        address sellerOracle,
        uint256 amount,
        bytes32 expectedDataHash,
        SafetyAttestation calldata attestation,
        bytes calldata gateSignature
    ) external nonReentrant {
        require(escrows[dealId].buyerAgent == address(0), "Deal already exists");

        bool hasValidSignature = false;
        if (gateSignature.length == 65) {
            _verifyAttestation(attestation, gateSignature);
            require(attestation.agentWallet == msg.sender, "Agent mismatch");
            require(amount <= attestation.maxAllowedSpend, "Exceeds max spend");
            hasValidSignature = true;
        }

        IERC20(address(usdc)).safeTransferFrom(msg.sender, address(this), amount);

        // Guarded: 0s unlock time (Instant finality), Unverified: 24h challenge lock
        uint256 unlockTimestamp = hasValidSignature ? block.timestamp : block.timestamp + 24 hours;

        escrows[dealId] = EscrowDeal({
            buyerAgent: msg.sender,
            sellerOracle: sellerOracle,
            amount: amount,
            expectedDataHash: expectedDataHash,
            unlockTime: unlockTimestamp,
            isGuarded: hasValidSignature,
            settled: false
        });

        emit EscrowCreated(dealId, msg.sender, sellerOracle, amount, hasValidSignature);
    }

    /**
     * @notice Releases escrow payout after unlock delay
     */
    function releaseEscrow(bytes32 dealId) external nonReentrant {
        EscrowDeal storage deal = escrows[dealId];
        require(!deal.settled, "Already settled");
        require(msg.sender == deal.buyerAgent || msg.sender == owner(), "Unauthorized");
        require(block.timestamp >= deal.unlockTime, "Challenge period active");

        deal.settled = true;

        uint256 appliedBps = deal.isGuarded ? guardedTakeRateBps : unverifiedTakeRateBps;
        uint256 fee = (deal.amount * appliedBps) / BPS_DENOMINATOR;
        if (deal.isGuarded) {
            fee += microTollFee;
        }

        uint256 sellerPayout = deal.amount - fee;

        _splitAndDistributeFee(fee);
        IERC20(address(usdc)).safeTransfer(deal.sellerOracle, sellerPayout);

        emit EscrowSettled(dealId, deal.sellerOracle, sellerPayout);
    }

    /**
     * @notice [Batch Settlement] Distributes accumulated micro-toll (Tier 1) balance gathered via Multicall3
     * @param totalBatchAmount Total USDC micro-tolls swept in this batch run
     */
    function sweepBatchMicroTolls(uint256 totalBatchAmount) external nonReentrant {
        require(msg.sender == relayerGasTank || msg.sender == owner(), "Only relayer or owner");
        uint256 routerBalance = IERC20(address(usdc)).balanceOf(address(this));
        require(routerBalance >= totalBatchAmount, "Insufficient collected balance");

        // Execute single atomic 70:20:10 protocol revenue distribution
        _splitAndDistributeFee(totalBatchAmount);
    }

    /**
     * @dev Automatic 70:20:10 protocol revenue distribution
     */
    function _splitAndDistributeFee(uint256 totalFee) internal {
        if (totalFee == 0) return;

        uint256 treasuryAmt = (totalFee * TREASURY_SHARE_BPS) / BPS_DENOMINATOR;
        uint256 insuranceAmt = (totalFee * INSURANCE_SHARE_BPS) / BPS_DENOMINATOR;
        uint256 relayerAmt = totalFee - treasuryAmt - insuranceAmt;

        IERC20 token = IERC20(address(usdc));
        token.safeTransfer(protocolTreasury, treasuryAmt);
        token.safeTransfer(insuranceVault, insuranceAmt);
        token.safeTransfer(relayerGasTank, relayerAmt);

        emit FeeDistributed(totalFee, treasuryAmt, insuranceAmt, relayerAmt);
    }
}

// ============================================================================
// 4. Safe{Wallet} On-Chain Guard Module (Treasury Drain Prevention)
// ============================================================================

contract SecurityGateSafeGuard is SecurityGateVerifier, ITransactionGuard {
    struct SpendPolicy {
        uint256 maxPerTx;        // Per-tx hard cap
        uint256 dailyLimit;      // 24-hour cumulative cap
        uint256 spentToday;      // Amount spent today
        uint256 lastResetDay;    // Day index (block.timestamp / 1 days)
    }

    mapping(address => SpendPolicy) public walletPolicies;

    error ExceedsPerTxCap(uint256 requested, uint256 maxAllowed);
    error ExceedsDailyCap(uint256 projected, uint256 dailyLimit);
    error MissingGateAttestationTail();
    error PayloadHashMismatch();

    constructor(address _gateSigner) SecurityGateVerifier(_gateSigner) {}

    /**
     * @notice Configures bounded wallet limits for the calling Safe
     */
    function configurePolicy(uint256 _maxPerTx, uint256 _dailyLimit) external {
        walletPolicies[msg.sender] = SpendPolicy({
            maxPerTx: _maxPerTx,
            dailyLimit: _dailyLimit,
            spentToday: 0,
            lastResetDay: block.timestamp / 1 days
        });
    }

    /**
     * @notice Safe execution interceptor hook called prior to execTransaction
     */
    function checkTransaction(
        address to,
        uint256 value,
        bytes memory data,
        EnumOperation operation,
        uint256, /* safeTxGas */
        uint256, /* baseGas */
        uint256, /* gasPrice */
        address, /* gasToken */
        address payable, /* refundReceiver */
        bytes memory signatures,
        address /* msgSender */
    ) external override {
        // Block delegatecall privilege escalation
        require(operation == EnumOperation.Call, "DelegateCall blocked by SecurityGate");

        address safeWallet = msg.sender;
        SpendPolicy storage policy = walletPolicies[safeWallet];

        // 1. Verify Bounded Wallet spend limits
        if (policy.maxPerTx > 0) {
            if (value > policy.maxPerTx) revert ExceedsPerTxCap(value, policy.maxPerTx);

            uint256 currentDay = block.timestamp / 1 days;
            if (currentDay > policy.lastResetDay) {
                policy.spentToday = 0;
                policy.lastResetDay = currentDay;
            }
            if (policy.spentToday + value > policy.dailyLimit) {
                revert ExceedsDailyCap(policy.spentToday + value, policy.dailyLimit);
            }
            policy.spentToday += value;
        }

        // 2. Compute canonical payload hash
        bytes32 actualPayloadHash = keccak256(abi.encodePacked(to, value, data));

        // 3. Verify gate attestation appended to signatures tail
        _extractAndVerifyGateTail(safeWallet, to, value, actualPayloadHash, signatures);
    }

    function _extractAndVerifyGateTail(
        address safeWallet,
        address to,
        uint256 value,
        bytes32 actualPayloadHash,
        bytes memory signatures
    ) internal {
        if (signatures.length <= 65) revert MissingGateAttestationTail();

        // Extract bytes following standard 65-byte Safe owner signature
        bytes memory gateBundle = new bytes(signatures.length - 65);
        for (uint256 i = 0; i < gateBundle.length; i++) {
            gateBundle[i] = signatures[i + 65];
        }

        (SafetyAttestation memory att, bytes memory gateSig) = abi.decode(
            gateBundle,
            (SafetyAttestation, bytes)
        );

        if (att.payloadHash != actualPayloadHash) revert PayloadHashMismatch();
        require(att.agentWallet == safeWallet, "Safe address mismatch");
        require(att.targetAddress == to, "Target address mismatch");
        require(value <= att.maxAllowedSpend, "Value exceeds attested spend");

        this.verifyExternalAttestation(att, gateSig);
    }

    function verifyExternalAttestation(
        SafetyAttestation calldata att,
        bytes calldata gateSig
    ) external {
        require(msg.sender == address(this), "Internal only");
        _verifyAttestation(att, gateSig);
    }

    function checkAfterExecution(bytes32, bool) external override {}
}
