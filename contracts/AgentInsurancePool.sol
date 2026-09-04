// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface IERC20 {
    function transferFrom(address sender, address recipient, uint256 amount) external returns (bool);
    function transfer(address recipient, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
}

/**
 * @title AgentInsurancePool
 * @notice Autonomous AI Agent Malpractice / Failure Insurance Protocol.
 *         Allows AI agents and hiring managers to purchase liability coverage against
 *         hallucinations, prompt injections, and execution failures.
 *         Claims are automatically adjudicated and disbursed via Security Gate Oracle EIP-712 attestations.
 */
contract AgentInsurancePool {
    IERC20 public immutable usdcToken;
    address public oracleSigner;
    address public oracleTreasury;
    address public owner;

    uint256 public totalCapital;              // Total LP capital in pool
    uint256 public totalUnderwrittenCoverage; // Active aggregate coverage liability
    uint256 public totalClaimsPaid;           // Historical claims paid out
    uint256 public totalPremiumsEarned;       // Historical premiums collected for LPs

    struct Policy {
        uint256 policyId;
        address agent;
        address beneficiary;
        uint256 coverageAmount;
        uint256 premiumPaid;
        uint256 createdAt;
        uint256 expiresAt;
        uint256 claimedAmount;
        bool isActive;
    }

    struct PolicyQuote {
        address agent;
        address beneficiary;
        uint256 coverageAmount;
        uint256 durationDays;
        uint256 premiumAmount;
        uint256 oracleFee;
        uint256 expiresAt;
        uint256 nonce;
        uint8 v;
        bytes32 r;
        bytes32 s;
    }

    struct ClaimAttestation {
        uint256 policyId;
        address claimant;
        uint256 claimAmount;
        bytes32 incidentHash;
        uint256 timestamp;
        uint256 nonce;
        uint8 v;
        bytes32 r;
        bytes32 s;
    }

    bytes32 public constant EIP712_DOMAIN_TYPEHASH = keccak256(
        "EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)"
    );

    bytes32 public constant POLICY_QUOTE_TYPEHASH = keccak256(
        "PolicyQuote(address agent,address beneficiary,uint256 coverageAmount,uint256 durationDays,uint256 premiumAmount,uint256 oracleFee,uint256 expiresAt,uint256 nonce)"
    );

    bytes32 public constant CLAIM_ATTESTATION_TYPEHASH = keccak256(
        "ClaimAttestation(uint256 policyId,address claimant,uint256 claimAmount,bytes32 incidentHash,uint256 timestamp,uint256 nonce)"
    );

    bytes32 public immutable DOMAIN_SEPARATOR;

    uint256 private _nextPolicyId = 1;
    mapping(uint256 => Policy) public policies;
    mapping(address => uint256[]) private _agentPolicies;
    mapping(address => uint256) public lpBalances;
    mapping(uint256 => bool) public executedNonces;

    // Events
    event CapitalDeposited(address indexed lp, uint256 amount);
    event CapitalWithdrawn(address indexed lp, uint256 amount);
    event PolicyPurchased(
        uint256 indexed policyId,
        address indexed agent,
        address indexed beneficiary,
        uint256 coverageAmount,
        uint256 premium,
        uint256 expiresAt
    );
    event ClaimDisbursed(
        uint256 indexed policyId,
        address indexed claimant,
        uint256 claimAmount,
        bytes32 incidentHash
    );
    event OracleSignerUpdated(address indexed oldSigner, address indexed newSigner);

    // Errors
    error Unauthorized();
    error InvalidSignature();
    error QuoteExpired();
    error PolicyExpiredOrInactive();
    error ExceedsCoverageLimit();
    error InsufficientPoolLiquidity();
    error NonceAlreadyUsed();
    error TransferFailed();

    modifier onlyOwner() {
        if (msg.sender != owner) revert Unauthorized();
        _;
    }

    constructor(address _usdcToken, address _oracleSigner, address _oracleTreasury) {
        owner = msg.sender;
        usdcToken = IERC20(_usdcToken);
        oracleSigner = _oracleSigner;
        oracleTreasury = _oracleTreasury;

        DOMAIN_SEPARATOR = keccak256(
            abi.encode(
                EIP712_DOMAIN_TYPEHASH,
                keccak256(bytes("AgentInsurancePool")),
                keccak256(bytes("1.0.0")),
                block.chainid,
                address(this)
            )
        );
    }

    // --- LP Capital Management ---

    function depositUnderwritingCapital(uint256 amount) external {
        if (amount == 0) revert TransferFailed();
        if (!usdcToken.transferFrom(msg.sender, address(this), amount)) revert TransferFailed();

        lpBalances[msg.sender] += amount;
        totalCapital += amount;

        emit CapitalDeposited(msg.sender, amount);
    }

    function withdrawCapital(uint256 amount) external {
        if (lpBalances[msg.sender] < amount) revert TransferFailed();
        if (address(this).balance < amount && usdcToken.balanceOf(address(this)) < amount) {
            revert InsufficientPoolLiquidity();
        }

        lpBalances[msg.sender] -= amount;
        totalCapital -= amount;

        if (!usdcToken.transfer(msg.sender, amount)) revert TransferFailed();

        emit CapitalWithdrawn(msg.sender, amount);
    }

    // --- Policy Purchase ---

    function purchasePolicy(PolicyQuote calldata quote) external returns (uint256) {
        if (block.timestamp > quote.expiresAt) revert QuoteExpired();
        if (executedNonces[quote.nonce]) revert NonceAlreadyUsed();
        executedNonces[quote.nonce] = true;

        // Verify Oracle Signature over PolicyQuote
        bytes32 structHash = keccak256(
            abi.encode(
                POLICY_QUOTE_TYPEHASH,
                quote.agent,
                quote.beneficiary,
                quote.coverageAmount,
                quote.durationDays,
                quote.premiumAmount,
                quote.oracleFee,
                quote.expiresAt,
                quote.nonce
            )
        );

        bytes32 digest = keccak256(abi.encodePacked("\x19\x01", DOMAIN_SEPARATOR, structHash));
        address recovered = ecrecover(digest, quote.v, quote.r, quote.s);
        if (recovered != oracleSigner) revert InvalidSignature();

        // Collect premium for LPs and fee for Oracle
        uint256 totalCost = quote.premiumAmount + quote.oracleFee;
        if (!usdcToken.transferFrom(msg.sender, address(this), quote.premiumAmount)) revert TransferFailed();
        if (quote.oracleFee > 0) {
            if (!usdcToken.transferFrom(msg.sender, oracleTreasury, quote.oracleFee)) revert TransferFailed();
        }

        uint256 policyId = _nextPolicyId++;
        uint256 durationSec = quote.durationDays * 1 days;
        uint256 policyExpiresAt = block.timestamp + durationSec;

        policies[policyId] = Policy({
            policyId: policyId,
            agent: quote.agent,
            beneficiary: quote.beneficiary,
            coverageAmount: quote.coverageAmount,
            premiumPaid: quote.premiumAmount,
            createdAt: block.timestamp,
            expiresAt: policyExpiresAt,
            claimedAmount: 0,
            isActive: true
        });

        _agentPolicies[quote.agent].push(policyId);
        totalUnderwrittenCoverage += quote.coverageAmount;
        totalPremiumsEarned += quote.premiumAmount;
        totalCapital += quote.premiumAmount; // Premiums accrue to pool liquidity

        emit PolicyPurchased(policyId, quote.agent, quote.beneficiary, quote.coverageAmount, quote.premiumAmount, policyExpiresAt);
        return policyId;
    }

    // --- Automated Claim Adjudication ---

    function claimCompensation(ClaimAttestation calldata claim) external {
        if (executedNonces[claim.nonce]) revert NonceAlreadyUsed();
        executedNonces[claim.nonce] = true;

        Policy storage p = policies[claim.policyId];
        if (!p.isActive || block.timestamp > p.expiresAt) revert PolicyExpiredOrInactive();
        if (p.claimedAmount + claim.claimAmount > p.coverageAmount) revert ExceedsCoverageLimit();
        if (claim.claimAmount > usdcToken.balanceOf(address(this))) revert InsufficientPoolLiquidity();

        // Verify Oracle Signature over ClaimAttestation
        bytes32 structHash = keccak256(
            abi.encode(
                CLAIM_ATTESTATION_TYPEHASH,
                claim.policyId,
                claim.claimant,
                claim.claimAmount,
                claim.incidentHash,
                claim.timestamp,
                claim.nonce
            )
        );

        bytes32 digest = keccak256(abi.encodePacked("\x19\x01", DOMAIN_SEPARATOR, structHash));
        address recovered = ecrecover(digest, claim.v, claim.r, claim.s);
        if (recovered != oracleSigner) revert InvalidSignature();

        // Disburse compensation instantly to beneficiary / claimant
        p.claimedAmount += claim.claimAmount;
        if (p.claimedAmount >= p.coverageAmount) {
            p.isActive = false;
        }

        totalCapital -= claim.claimAmount;
        totalClaimsPaid += claim.claimAmount;
        if (totalUnderwrittenCoverage >= claim.claimAmount) {
            totalUnderwrittenCoverage -= claim.claimAmount;
        }

        if (!usdcToken.transfer(claim.claimant, claim.claimAmount)) revert TransferFailed();

        emit ClaimDisbursed(claim.policyId, claim.claimant, claim.claimAmount, claim.incidentHash);
    }

    // --- Views ---

    function getPolicy(uint256 policyId) external view returns (Policy memory) {
        return policies[policyId];
    }

    function getAgentPolicies(address agent) external view returns (uint256[] memory) {
        return _agentPolicies[agent];
    }

    function getSolvencyMetrics() external view returns (
        uint256 poolCapital,
        uint256 activeCoverage,
        uint256 claimsPaid,
        uint256 premiumsEarned
    ) {
        return (totalCapital, totalUnderwrittenCoverage, totalClaimsPaid, totalPremiumsEarned);
    }

    function setOracleSigner(address _newSigner) external onlyOwner {
        emit OracleSignerUpdated(oracleSigner, _newSigner);
        oracleSigner = _newSigner;
    }
}
