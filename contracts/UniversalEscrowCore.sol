// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./ITruthAdapter.sol";

interface IERC20 {
    function transferFrom(address sender, address recipient, uint256 amount) external returns (bool);
    function transfer(address recipient, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
}

/**
 * @title UniversalEscrowCore
 * @notice Modular, Lego-like Universal Escrow & Direct Settlement Engine for Real-World Economy.
 *         Unifies Maritime Freight, Bio/Pharma IP, and Construction Infrastructure escrows into
 *         a single, hyper-optimized smart contract on Polygon, Base, and Arbitrum.
 *
 *         Key Features:
 *         1. Off-chain compute validation via pluggable ITruthAdapter contracts.
 *         2. EIP-712 Cryptographic Proof-of-Truth Oracle Signature verification.
 *         3. Direct Split Payout: Bypasses predatory general contractors & middlemen,
 *            disbursing funds directly to laborers, suppliers, and researchers in <1 second.
 *         4. Sub-cent gas footprint with 0.25% protocol fee to A.GRID Treasury.
 */
contract UniversalEscrowCore {
    // Protocol parameters
    address public oracleSigner;
    address public governance;
    address public treasury;
    uint256 public constant PROTOCOL_FEE_BPS = 25; // 0.25% clearing toll
    uint256 public constant BPS_DENOMINATOR = 10000;

    // Mutex for Reentrancy Protection
    uint256 private _locked = 1;
    modifier nonReentrant() {
        require(_locked == 1, "REENTRANCY_GUARD");
        _locked = 2;
        _;
        _locked = 1;
    }

    modifier onlyGovernance() {
        require(msg.sender == governance, "ONLY_GOVERNANCE");
        _;
    }

    struct SplitRecipient {
        address recipient; // Laborer, material supplier, research team wallet
        uint256 amount;    // Disbursal amount in token base units
    }

    struct EscrowJob {
        bytes32 jobId;
        address payer;              // Enterprise client / Big pharma / Import company
        address token;              // ERC-20 payment token (USDC, EURC, etc.)
        uint256 totalDeposit;       // Locked escrow capital
        ITruthAdapter.IndustryDomain domain;
        address truthAdapter;       // Pluggable domain truth adapter contract
        bytes32 truthHashRequirement;// Expected hash of physical proof (BIM hash, ZK root, RFID log)
        uint256 createdAt;
        uint256 deadline;
        bool isSettled;
        bool isRefunded;
    }

    // Storage mappings
    mapping(bytes32 => EscrowJob) public jobs;
    mapping(ITruthAdapter.IndustryDomain => address) public domainAdapters;

    // EIP-712 Domain Separator & Typehashes
    bytes32 public constant EIP712_DOMAIN_TYPEHASH = keccak256(
        "EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)"
    );
    bytes32 public constant TRUTH_SETTLEMENT_TYPEHASH = keccak256(
        "TruthSettlementAttestation(bytes32 jobId,uint8 domain,bytes32 truthHashRequirement,bytes32 recipientsHash,uint256 expiresAt)"
    );
    bytes32 public constant BATCH_SETTLEMENT_TYPEHASH = keccak256(
        "BatchSettlementAttestation(bytes32 merkleRoot,address token,uint256 totalAmount,uint256 totalCount,uint256 expiresAt)"
    );
    bytes32 public constant ADVERSARIAL_SLASH_TYPEHASH = keccak256(
        "AdversarialExploitEvidence(address attackerAgent,address token,bytes32 payloadHash,uint8 violationType,uint256 penaltyAmount,uint256 timestamp)"
    );
    bytes32 public immutable DOMAIN_SEPARATOR;

    // Worker stake balances: worker => token => balance
    mapping(address => mapping(address => uint256)) public workerStakes;
    mapping(bytes32 => bool) public settledBatches;
    uint256 public constant DEFAULT_SLASH_PENALTY = 10 * 10**6; // 10.00 USDC (6 decimals)

    // Events
    event EscrowDeposited(
        bytes32 indexed jobId,
        address indexed payer,
        address indexed token,
        uint256 amount,
        ITruthAdapter.IndustryDomain domain,
        bytes32 truthHashRequirement,
        uint256 deadline
    );
    event DirectSettlementExecuted(
        bytes32 indexed jobId,
        uint256 totalDisbursed,
        uint256 protocolFee,
        uint256 recipientCount
    );
    event EscrowRefunded(bytes32 indexed jobId, address indexed payer, uint256 amount);
    event DomainAdapterUpdated(ITruthAdapter.IndustryDomain indexed domain, address indexed adapter);
    event OracleSignerUpdated(address indexed oldSigner, address indexed newSigner);
    event TreasuryUpdated(address indexed oldTreasury, address indexed newTreasury);
    event MicroBatchSettled(bytes32 indexed merkleRoot, address indexed token, uint256 totalAmount, uint256 totalCount);
    event WorkerStakeDeposited(address indexed worker, address indexed token, uint256 amount);
    event WorkerStakeWithdrawn(address indexed worker, address indexed token, uint256 amount);
    event AdversarySlashed(address indexed attackerAgent, address indexed token, uint8 violationType, uint256 penaltyAmount, address slasher);

    constructor(address _oracleSigner, address _treasury) {
        require(_oracleSigner != address(0), "INVALID_ORACLE_SIGNER");
        require(_treasury != address(0), "INVALID_TREASURY");

        oracleSigner = _oracleSigner;
        treasury = _treasury;
        governance = msg.sender;

        DOMAIN_SEPARATOR = keccak256(
            abi.encode(
                EIP712_DOMAIN_TYPEHASH,
                keccak256(bytes("UniversalEscrowCore")),
                keccak256(bytes("1.0.0")),
                block.chainid,
                address(this)
            )
        );
    }

    /**
     * @notice Registers or updates a domain truth adapter (e.g. TradeIoT, BioZk, BuildDrone)
     */
    function setDomainAdapter(ITruthAdapter.IndustryDomain domain, address adapter) external onlyGovernance {
        domainAdapters[domain] = adapter;
        emit DomainAdapterUpdated(domain, adapter);
    }

    /**
     * @notice Updates the trusted off-chain micro-oracle signer
     */
    function setOracleSigner(address newSigner) external onlyGovernance {
        require(newSigner != address(0), "INVALID_SIGNER");
        emit OracleSignerUpdated(oracleSigner, newSigner);
        oracleSigner = newSigner;
    }

    /**
     * @notice Updates protocol treasury destination
     */
    function setTreasury(address newTreasury) external onlyGovernance {
        require(newTreasury != address(0), "INVALID_TREASURY");
        emit TreasuryUpdated(treasury, newTreasury);
        treasury = newTreasury;
    }

    /**
     * @notice 1. Universal Capital Lock-up function across all industries
     * @param jobId Unique 32-byte identifier for the escrow agreement
     * @param token Address of ERC20 payment asset (e.g. USDC)
     * @param amount Deposit amount
     * @param domain Target industry sector (0=Maritime, 1=Bio, 2=Construction)
     * @param truthHashRequirement The cryptographic digest required to unlock funds
     * @param durationSec Duration in seconds until expiration refund is unlocked
     */
    function depositEscrow(
        bytes32 jobId,
        address token,
        uint256 amount,
        ITruthAdapter.IndustryDomain domain,
        bytes32 truthHashRequirement,
        uint256 durationSec
    ) external nonReentrant {
        require(amount > 0, "ZERO_DEPOSIT");
        require(jobs[jobId].totalDeposit == 0, "JOB_ALREADY_EXISTS");
        require(durationSec >= 300, "MIN_DURATION_5_MINUTES");

        address adapter = domainAdapters[domain];

        // Safe transfer tokens into this vault
        require(IERC20(token).transferFrom(msg.sender, address(this), amount), "TRANSFER_FROM_FAILED");

        jobs[jobId] = EscrowJob({
            jobId: jobId,
            payer: msg.sender,
            token: token,
            totalDeposit: amount,
            domain: domain,
            truthAdapter: adapter,
            truthHashRequirement: truthHashRequirement,
            createdAt: block.timestamp,
            deadline: block.timestamp + durationSec,
            isSettled: false,
            isRefunded: false
        });

        emit EscrowDeposited(jobId, msg.sender, token, amount, domain, truthHashRequirement, block.timestamp + durationSec);
    }

    /**
     * @notice 2. Direct Split Settlement upon Physical/Mathematical Truth Verification
     * @param jobId Unique 32-byte escrow identifier
     * @param recipients Array of beneficiaries (laborers, suppliers, researchers) with individual amounts
     * @param truthPayload Cryptographic sensor logs, LiDAR scan ratio, or ZK-Proof data
     * @param expiresAt Signature expiration timestamp
     * @param v ECDSA recovery byte
     * @param r ECDSA signature component
     * @param s ECDSA signature component
     */
    function executeSettlementWithProof(
        bytes32 jobId,
        SplitRecipient[] calldata recipients,
        bytes calldata truthPayload,
        uint256 expiresAt,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) external nonReentrant {
        EscrowJob storage job = jobs[jobId];
        require(job.totalDeposit > 0, "JOB_DOES_NOT_EXIST");
        require(!job.isSettled, "ALREADY_SETTLED");
        require(!job.isRefunded, "ALREADY_REFUNDED");
        require(block.timestamp <= expiresAt, "ATTESTATION_EXPIRED");
        require(recipients.length > 0, "EMPTY_RECIPIENTS");

        // 1) Verify physical/mathematical truth via pluggable adapter (if configured)
        if (job.truthAdapter != address(0)) {
            require(
                ITruthAdapter(job.truthAdapter).verifyTruth(jobId, truthPayload),
                "PHYSICAL_TRUTH_VALIDATION_FAILED"
            );
        }

        // 2) Verify EIP-712 Cryptographic Attestation from Security Gate Oracle
        bytes32 recipientsHash = keccak256(abi.encode(recipients));
        bytes32 structHash = keccak256(
            abi.encode(
                TRUTH_SETTLEMENT_TYPEHASH,
                jobId,
                uint8(job.domain),
                job.truthHashRequirement,
                recipientsHash,
                expiresAt
            )
        );
        bytes32 digest = keccak256(abi.encodePacked("\x19\x01", DOMAIN_SEPARATOR, structHash));
        address recoveredSigner = ecrecover(digest, v, r, s);
        require(recoveredSigner == oracleSigner, "INVALID_ORACLE_SIGNATURE");

        job.isSettled = true;

        // 3) Calculate Protocol Fee (0.25%)
        uint256 protocolFee = (job.totalDeposit * PROTOCOL_FEE_BPS) / BPS_DENOMINATOR;
        uint256 totalDisbursed = 0;

        // 4) Execute Direct Split Payout (Instant disintermediation)
        address token = job.token;
        for (uint256 i = 0; i < recipients.length; i++) {
            uint256 payAmt = recipients[i].amount;
            address recipientAddr = recipients[i].recipient;
            require(recipientAddr != address(0), "INVALID_RECIPIENT_ADDRESS");
            require(payAmt > 0, "INVALID_RECIPIENT_AMOUNT");

            totalDisbursed += payAmt;
            require(IERC20(token).transfer(recipientAddr, payAmt), "RECIPIENT_TRANSFER_FAILED");
        }

        require(totalDisbursed + protocolFee <= job.totalDeposit, "EXCEEDS_ESCROW_DEPOSIT");

        // Send Protocol Fee to A.GRID Treasury
        if (protocolFee > 0) {
            require(IERC20(token).transfer(treasury, protocolFee), "TREASURY_TRANSFER_FAILED");
        }

        // Return any remaining residual dust back to payer
        uint256 residual = job.totalDeposit - (totalDisbursed + protocolFee);
        if (residual > 0) {
            require(IERC20(token).transfer(job.payer, residual), "RESIDUAL_REFUND_FAILED");
        }

        emit DirectSettlementExecuted(jobId, totalDisbursed, protocolFee, recipients.length);
    }

    /**
     * @notice 3. Refund escrow deposit back to payer if task expired without verified settlement
     */
    function refundEscrow(bytes32 jobId) external nonReentrant {
        EscrowJob storage job = jobs[jobId];
        require(job.totalDeposit > 0, "JOB_DOES_NOT_EXIST");
        require(!job.isSettled, "ALREADY_SETTLED");
        require(!job.isRefunded, "ALREADY_REFUNDED");
        require(block.timestamp > job.deadline, "DEADLINE_NOT_REACHED");
        require(msg.sender == job.payer || msg.sender == governance, "NOT_AUTHORIZED");

        job.isRefunded = true;
        uint256 amountToRefund = job.totalDeposit;

        require(IERC20(job.token).transfer(job.payer, amountToRefund), "REFUND_TRANSFER_FAILED");

        emit EscrowRefunded(jobId, job.payer, amountToRefund);
    }

    /**
     * @notice 4. Deposit collateral stake required for agentic work and escrow claiming
     */
    function depositWorkerStake(address token, uint256 amount) external nonReentrant {
        require(amount > 0, "ZERO_STAKE_AMOUNT");
        require(IERC20(token).transferFrom(msg.sender, address(this), amount), "STAKE_TRANSFER_FAILED");
        workerStakes[msg.sender][token] += amount;
        emit WorkerStakeDeposited(msg.sender, token, amount);
    }

    /**
     * @notice 5. Withdraw unslashed collateral stake
     */
    function withdrawWorkerStake(address token, uint256 amount) external nonReentrant {
        require(amount > 0, "ZERO_WITHDRAW_AMOUNT");
        require(workerStakes[msg.sender][token] >= amount, "INSUFFICIENT_WORKER_STAKE");
        workerStakes[msg.sender][token] -= amount;
        require(IERC20(token).transfer(msg.sender, amount), "WITHDRAW_TRANSFER_FAILED");
        emit WorkerStakeWithdrawn(msg.sender, token, amount);
    }

    /**
     * @notice 6. State Channel Merkle Batch Settlement: Settles hundreds of $0.002 micro-payments in 1 tx
     */
    function settleMicroBatch(
        bytes32 merkleRoot,
        address token,
        uint256 totalAmount,
        uint256 totalCount,
        uint256 expiresAt,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) external nonReentrant {
        require(!settledBatches[merkleRoot], "BATCH_ALREADY_SETTLED");
        require(block.timestamp <= expiresAt, "BATCH_ATTESTATION_EXPIRED");
        require(totalAmount > 0 && totalCount > 0, "INVALID_BATCH_PARAMETERS");

        // Verify EIP-712 Attestation from Protocol Oracle
        bytes32 structHash = keccak256(
            abi.encode(
                BATCH_SETTLEMENT_TYPEHASH,
                merkleRoot,
                token,
                totalAmount,
                totalCount,
                expiresAt
            )
        );
        bytes32 digest = keccak256(abi.encodePacked("\x19\x01", DOMAIN_SEPARATOR, structHash));
        address recoveredSigner = ecrecover(digest, v, r, s);
        require(recoveredSigner == oracleSigner, "INVALID_BATCH_ORACLE_SIGNATURE");

        settledBatches[merkleRoot] = true;

        // Disburse protocol fees directly into Treasury
        require(IERC20(token).transfer(treasury, totalAmount), "BATCH_TREASURY_TRANSFER_FAILED");

        emit MicroBatchSettled(merkleRoot, token, totalAmount, totalCount);
    }

    /**
     * @notice 7. Deterministic Slashing: Confiscates $10.00 collateral from adversarial attacking agents
     */
    function slashAdversary(
        address attackerAgent,
        address token,
        bytes32 payloadHash,
        uint8 violationType,
        uint256 timestamp,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) external nonReentrant {
        require(attackerAgent != address(0), "INVALID_ATTACKER_ADDRESS");
        require(workerStakes[attackerAgent][token] >= DEFAULT_SLASH_PENALTY, "INSUFFICIENT_COLLATERAL_TO_SLASH");

        // Verify Proof-of-Exploit Evidence signed by Security Gate Oracle
        bytes32 structHash = keccak256(
            abi.encode(
                ADVERSARIAL_SLASH_TYPEHASH,
                attackerAgent,
                token,
                payloadHash,
                violationType,
                DEFAULT_SLASH_PENALTY,
                timestamp
            )
        );
        bytes32 digest = keccak256(abi.encodePacked("\x19\x01", DOMAIN_SEPARATOR, structHash));
        address recoveredSigner = ecrecover(digest, v, r, s);
        require(recoveredSigner == oracleSigner, "INVALID_SLASH_ORACLE_SIGNATURE");

        // Deduct penalty from attacker's staked balance
        workerStakes[attackerAgent][token] -= DEFAULT_SLASH_PENALTY;

        // Split penalty: 80% to Treasury, 20% to Reporter / Slasher as bounty
        uint256 treasuryShare = (DEFAULT_SLASH_PENALTY * 80) / 100;
        uint256 reporterShare = DEFAULT_SLASH_PENALTY - treasuryShare;

        require(IERC20(token).transfer(treasury, treasuryShare), "SLASH_TREASURY_TRANSFER_FAILED");
        require(IERC20(token).transfer(msg.sender, reporterShare), "SLASH_REPORTER_TRANSFER_FAILED");

        emit AdversarySlashed(attackerAgent, token, violationType, DEFAULT_SLASH_PENALTY, msg.sender);
    }
}
