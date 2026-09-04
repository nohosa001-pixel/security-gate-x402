// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface IERC20 {
    function transferFrom(address sender, address recipient, uint256 amount) external returns (bool);
    function transfer(address recipient, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
}

/**
 * @title AgentEscrow
 * @notice Autonomous Agent-to-Agent (M2M) Task Escrow & Proof-of-Safety Slashing Protocol.
 *         Ensures autonomous task deliverables are cryptographically audited for hallucinations
 *         and code/injection threats before capital is released or slashed.
 */
contract AgentEscrow {
    address public oracleSigner;
    address public owner;
    IERC20 public immutable paymentToken;
    uint8 public maxAcceptableRiskScore = 25; // Out of 100

    enum JobStatus {
        Created,    // Client funded payout, waiting for worker stake
        Staked,     // Worker deposited collateral, task in progress
        Completed,  // Oracle attested PASSED -> Payout & Stake released to worker
        Slashed,    // Oracle attested BLOCKED -> Stake forfeited to client, payout refunded
        Refunded    // Expired or cancelled before staking
    }

    struct Job {
        uint256 jobId;
        address client;
        address worker;
        uint256 payoutAmount;
        uint256 stakeAmount;
        bytes32 specHash;
        JobStatus status;
        uint256 createdAt;
        uint256 deadline;
    }

    struct EscrowAttestation {
        uint256 jobId;
        bytes32 deliverableHash;
        uint8 riskScore;
        string verdict;
        uint256 expiresAt;
        uint8 v;
        bytes32 r;
        bytes32 s;
    }

    bytes32 public constant EIP712_DOMAIN_TYPEHASH = keccak256(
        "EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)"
    );

    bytes32 public constant ESCROW_ATTESTATION_TYPEHASH = keccak256(
        "EscrowAttestation(uint256 jobId,bytes32 deliverableHash,uint8 riskScore,string verdict,uint256 expiresAt)"
    );

    bytes32 public immutable DOMAIN_SEPARATOR;

    uint256 private _nextJobId = 1;
    mapping(uint256 => Job) public jobs;

    // Events
    event JobCreated(uint256 indexed jobId, address indexed client, address indexed worker, uint256 payout, bytes32 specHash);
    event JobStaked(uint256 indexed jobId, address indexed worker, uint256 stakeAmount);
    event JobCompleted(uint256 indexed jobId, address indexed worker, uint256 totalPayout, uint8 riskScore);
    event JobSlashed(uint256 indexed jobId, address indexed client, uint256 refundAndBounty, uint8 riskScore);
    event OracleSignerUpdated(address indexed oldSigner, address indexed newSigner);

    // Errors
    error Unauthorized();
    error InvalidStatus(JobStatus current, JobStatus required);
    error InvalidOracleSignature();
    error AttestationExpired();
    error JobDeadlinePassed();
    error TransferFailed();
    error InsufficientStake();

    modifier onlyOwner() {
        if (msg.sender != owner) revert Unauthorized();
        _;
    }

    constructor(address _paymentToken, address _oracleSigner) {
        owner = msg.sender;
        paymentToken = IERC20(_paymentToken);
        oracleSigner = _oracleSigner;

        DOMAIN_SEPARATOR = keccak256(
            abi.encode(
                EIP712_DOMAIN_TYPEHASH,
                keccak256(bytes("AgentEscrowOracle")),
                keccak256(bytes("1.0.0")),
                block.chainid,
                address(this)
            )
        );
    }

    function setOracleSigner(address _newSigner) external onlyOwner {
        emit OracleSignerUpdated(oracleSigner, _newSigner);
        oracleSigner = _newSigner;
    }

    function setMaxAcceptableRiskScore(uint8 _newMax) external onlyOwner {
        maxAcceptableRiskScore = _newMax;
    }

    /**
     * @notice Client agent creates an escrow task and deposits the task payout amount.
     */
    function createJob(
        address worker,
        uint256 payoutAmount,
        uint256 requiredStake,
        bytes32 specHash,
        uint256 durationSeconds
    ) external returns (uint256) {
        if (payoutAmount > 0) {
            if (!paymentToken.transferFrom(msg.sender, address(this), payoutAmount)) revert TransferFailed();
        }

        uint256 jobId = _nextJobId++;
        jobs[jobId] = Job({
            jobId: jobId,
            client: msg.sender,
            worker: worker,
            payoutAmount: payoutAmount,
            stakeAmount: requiredStake,
            specHash: specHash,
            status: JobStatus.Created,
            createdAt: block.timestamp,
            deadline: block.timestamp + durationSeconds
        });

        emit JobCreated(jobId, msg.sender, worker, payoutAmount, specHash);
        return jobId;
    }

    /**
     * @notice Worker agent accepts the task and stakes collateral against malicious/hallucinated work.
     */
    function depositStake(uint256 jobId) external {
        Job storage job = jobs[jobId];
        if (job.status != JobStatus.Created) revert InvalidStatus(job.status, JobStatus.Created);
        if (block.timestamp > job.deadline) revert JobDeadlinePassed();
        if (msg.sender != job.worker && job.worker != address(0)) revert Unauthorized();

        // If worker was unspecified, caller binds as worker
        if (job.worker == address(0)) {
            job.worker = msg.sender;
        }

        if (job.stakeAmount > 0) {
            if (!paymentToken.transferFrom(msg.sender, address(this), job.stakeAmount)) revert TransferFailed();
        }

        job.status = JobStatus.Staked;
        emit JobStaked(jobId, msg.sender, job.stakeAmount);
    }

    /**
     * @notice Completes job and releases payout + stake to worker upon valid Oracle PASSED proof.
     */
    function completeJob(uint256 jobId, EscrowAttestation calldata proof) external {
        Job storage job = jobs[jobId];
        if (job.status != JobStatus.Staked) revert InvalidStatus(job.status, JobStatus.Staked);

        _verifyAttestation(jobId, proof);

        // Verify Oracle verdict passed and risk is below ceiling
        if (proof.riskScore > maxAcceptableRiskScore || keccak256(bytes(proof.verdict)) != keccak256(bytes("PASSED"))) {
            revert Unauthorized();
        }

        job.status = JobStatus.Completed;
        uint256 totalRelease = job.payoutAmount + job.stakeAmount;

        if (totalRelease > 0) {
            if (!paymentToken.transfer(job.worker, totalRelease)) revert TransferFailed();
        }

        emit JobCompleted(jobId, job.worker, totalRelease, proof.riskScore);
    }

    /**
     * @notice Slashes worker stake and refunds client upon valid Oracle BLOCKED proof (hallucination or exploit).
     */
    function slashJob(uint256 jobId, EscrowAttestation calldata proof) external {
        Job storage job = jobs[jobId];
        if (job.status != JobStatus.Staked) revert InvalidStatus(job.status, JobStatus.Staked);

        _verifyAttestation(jobId, proof);

        // Slashing requires Oracle proof showing BLOCKED or excessive risk
        if (proof.riskScore <= maxAcceptableRiskScore && keccak256(bytes(proof.verdict)) == keccak256(bytes("PASSED"))) {
            revert Unauthorized();
        }

        job.status = JobStatus.Slashed;
        uint256 totalRefundAndBounty = job.payoutAmount + job.stakeAmount;

        if (totalRefundAndBounty > 0) {
            // Client receives original payout back + slashed worker stake as compensation
            if (!paymentToken.transfer(job.client, totalRefundAndBounty)) revert TransferFailed();
        }

        emit JobSlashed(jobId, job.client, totalRefundAndBounty, proof.riskScore);
    }

    /**
     * @notice Internal EIP-712 cryptographic signature verification against oracleSigner.
     */
    function _verifyAttestation(uint256 jobId, EscrowAttestation calldata proof) internal view {
        if (proof.jobId != jobId) revert Unauthorized();
        if (block.timestamp > proof.expiresAt) revert AttestationExpired();

        bytes32 structHash = keccak256(
            abi.encode(
                ESCROW_ATTESTATION_TYPEHASH,
                proof.jobId,
                proof.deliverableHash,
                proof.riskScore,
                keccak256(bytes(proof.verdict)),
                proof.expiresAt
            )
        );

        bytes32 digest = keccak256(abi.encodePacked("\x19\x01", DOMAIN_SEPARATOR, structHash));
        address recovered = ecrecover(digest, proof.v, proof.r, proof.s);

        if (recovered != oracleSigner) revert InvalidOracleSignature();
    }
}
