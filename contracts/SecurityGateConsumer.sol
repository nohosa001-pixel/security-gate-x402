// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title SecurityGateConsumer
 * @notice Verifies cryptographic EIP-712 Proof-of-Safety attestations issued by Agent Security Gate x402
 *         before executing autonomous on-chain agent actions on Polygon, Base, or Arbitrum.
 */
contract SecurityGateConsumer {
    address public oracleSigner;
    address public owner;

    bytes32 public constant EIP712_DOMAIN_TYPEHASH = keccak256(
        "EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)"
    );

    bytes32 public constant ATTESTATION_TYPEHASH = keccak256(
        "SecurityAttestation(bytes32 payloadHash,uint8 riskScore,string verdict,uint256 expiresAt)"
    );

    bytes32 public DOMAIN_SEPARATOR;

    // Events
    event SecurityAttestationVerified(bytes32 indexed payloadHash, uint8 riskScore, string verdict, address indexed agent);
    event ActionExecuted(bytes32 indexed payloadHash, address indexed target, bytes data);
    event OracleSignerUpdated(address indexed oldSigner, address indexed newSigner);

    error InvalidOracleSignature();
    error AttestationExpired();
    error ExcessiveRiskScore(uint8 riskScore, uint8 maxAllowed);
    error Unauthorized();

    modifier onlyOwner() {
        if (msg.sender != owner) revert Unauthorized();
        _;
    }

    constructor(address _oracleSigner) {
        owner = msg.sender;
        oracleSigner = _oracleSigner;

        DOMAIN_SEPARATOR = keccak256(
            abi.encode(
                EIP712_DOMAIN_TYPEHASH,
                keccak256(bytes("AgentSecurityGateOracle")),
                keccak256(bytes("1.0.0")),
                block.chainid,
                address(0) // Domain matches oracle zero-verifyingContract default
            )
        );
    }

    function setOracleSigner(address _newSigner) external onlyOwner {
        emit OracleSignerUpdated(oracleSigner, _newSigner);
        oracleSigner = _newSigner;
    }

    /**
     * @notice Verifies oracle attestation and executes authorized agent target call.
     */
    function verifyAndExecute(
        bytes32 payloadHash,
        uint8 riskScore,
        string calldata verdict,
        uint256 expiresAt,
        uint8 v,
        bytes32 r,
        bytes32 s,
        address target,
        bytes calldata callData,
        uint8 maxRiskScore
    ) external returns (bytes memory) {
        if (block.timestamp > expiresAt) revert AttestationExpired();
        if (riskScore > maxRiskScore) revert ExcessiveRiskScore(riskScore, maxRiskScore);

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

        emit SecurityAttestationVerified(payloadHash, riskScore, verdict, msg.sender);

        (bool success, bytes memory result) = target.call(callData);
        require(success, "Target execution failed");

        emit ActionExecuted(payloadHash, target, callData);
        return result;
    }
}
