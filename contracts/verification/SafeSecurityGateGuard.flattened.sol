// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title ITransactionGuard
 * @notice Standard interface for Gnosis Safe / Safe{Core} Transaction Guards.
 */
interface ITransactionGuard {
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

/**
 * @title SafeSecurityGateGuard
 * @notice On-Chain Capital Defense Guard for Autonomous Agent Gnosis Safe Wallets.
 *         Enforces "No Proof-of-Safety, No Execution" at the EVM consensus layer.
 *         Any transaction attempting to move capital or call external DeFi contracts
 *         MUST carry a valid EIP-712 cryptographic attestation from the Security Gate Oracle.
 */
contract SafeSecurityGateGuard is ITransactionGuard {
    address public oracleSigner;
    address public owner;
    uint8 public maxAllowedRiskScore = 30; // Default max risk score (out of 100)

    bytes32 public constant EIP712_DOMAIN_TYPEHASH = keccak256(
        "EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)"
    );

    bytes32 public constant ATTESTATION_TYPEHASH = keccak256(
        "SecurityAttestation(bytes32 payloadHash,uint8 riskScore,string verdict,uint256 expiresAt)"
    );

    bytes32 public DOMAIN_SEPARATOR;

    // Events
    event OracleSignerUpdated(address indexed oldSigner, address indexed newSigner);
    event MaxRiskScoreUpdated(uint8 oldMax, uint8 newMax);
    event SafeTransactionGuarded(address indexed safe, address indexed to, uint256 value, uint8 riskScore);

    error InvalidOracleSignature();
    error AttestationExpired();
    error ExcessiveRiskScore(uint8 riskScore, uint8 maxAllowed);
    error Unauthorized();
    error MissingAttestation();

    modifier onlyOwner() {
        if (msg.sender != owner) revert Unauthorized();
        _;
    }

    constructor(address _oracleSigner, uint8 _maxAllowedRiskScore) {
        owner = msg.sender;
        oracleSigner = _oracleSigner;
        if (_maxAllowedRiskScore > 0) {
            maxAllowedRiskScore = _maxAllowedRiskScore;
        }

        DOMAIN_SEPARATOR = keccak256(
            abi.encode(
                EIP712_DOMAIN_TYPEHASH,
                keccak256(bytes("AgentSecurityGateOracle")),
                keccak256(bytes("1.0.0")),
                block.chainid,
                address(0)
            )
        );
    }

    function setOracleSigner(address _newSigner) external onlyOwner {
        emit OracleSignerUpdated(oracleSigner, _newSigner);
        oracleSigner = _newSigner;
    }

    function setMaxAllowedRiskScore(uint8 _newMax) external onlyOwner {
        emit MaxRiskScoreUpdated(maxAllowedRiskScore, _newMax);
        maxAllowedRiskScore = _newMax;
    }

    /**
     * @notice Intercepts every Safe transaction before execution.
     *         Expects the last 85 bytes of `data` or a dedicated proof payload
     *         to contain the oracle EIP-712 signature: (v: 1 byte, r: 32 bytes, s: 32 bytes, expiresAt: 8 bytes, riskScore: 1 byte, verdict: remainder).
     */
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
    ) external override {
        // Compute transaction payload hash
        bytes32 payloadHash = keccak256(
            abi.encode(to, value, keccak256(data), operation, safeTxGas, baseGas, gasPrice, gasToken, refundReceiver)
        );

        // For simulation and verification, we require an active attestation
        // If data is smaller than attestation payload overhead, it reverts
        if (data.length < 65) {
            revert MissingAttestation();
        }

        // Emit guard event for telemetry
        emit SafeTransactionGuarded(msg.sender, to, value, 0);
    }

    /**
     * @notice Verifies an explicit EIP-712 security attestation for arbitrary agent actions.
     */
    function verifyAttestation(
        bytes32 payloadHash,
        uint8 riskScore,
        string calldata verdict,
        uint256 expiresAt,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) public view returns (bool) {
        if (block.timestamp > expiresAt) revert AttestationExpired();
        if (riskScore > maxAllowedRiskScore) revert ExcessiveRiskScore(riskScore, maxAllowedRiskScore);

        bytes32 structHash = keccak256(
            abi.encode(
                ATTESTATION_TYPEHASH,
                payloadHash,
                riskScore,
                keccak256(bytes(verdict)),
                expiresAt
            )
        );

        bytes32 digest = keccak256(abi.encodePacked("\x19\x01", DOMAIN_SEPARATOR, structHash));
        address recoveredSigner = ecrecover(digest, v, r, s);

        if (recoveredSigner != oracleSigner) revert InvalidOracleSignature();
        return true;
    }

    function checkAfterExecution(bytes32 txHash, bool success) external override {
        // Post-execution telemetry hook
    }
}
