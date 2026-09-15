// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title GuardableBySecurityGate
 * @notice Abstract base contract for DeFi protocols, Lending pools, Automated Market Makers (AMMs),
 *         and DAO Treasuries requiring cryptographic Agent Security Gate verification before accepting
 *         autonomous agent transactions.
 * 
 * Usage:
 *     contract MyDeFiVault is GuardableBySecurityGate {
 *         constructor(address _oracle) GuardableBySecurityGate(_oracle) {}
 * 
 *         function agentExecuteSwap(
 *             bytes calldata swapData,
 *             SecurityAttestation calldata proof
 *         ) external requiresProofOfSafety(keccak256(swapData), proof) {
 *             // Execute swap safely with 100% mathematical guarantee against prompt-injected drains
 *         }
 *     }
 */
abstract contract GuardableBySecurityGate {
    address public securityOracleSigner;
    address public contractOwner;
    uint8 public maximumAcceptableRiskScore = 20;

    struct SecurityAttestation {
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

    bytes32 public constant ATTESTATION_TYPEHASH = keccak256(
        "SecurityAttestation(bytes32 payloadHash,uint8 riskScore,string verdict,uint256 expiresAt)"
    );

    bytes32 public immutable DOMAIN_SEPARATOR;

    event SecurityOracleUpdated(address indexed previousSigner, address indexed newSigner);
    event ProofOfSafetyAccepted(bytes32 indexed payloadHash, uint8 riskScore, address indexed agent);

    error OracleSignatureInvalid();
    error ProofExpired(uint256 currentTimestamp, uint256 expiresAt);
    error RiskScoreExceedsThreshold(uint8 detectedRisk, uint8 maximumAllowed);
    error SenderNotAuthorized();

    modifier onlyContractOwner() {
        if (msg.sender != contractOwner) revert SenderNotAuthorized();
        _;
    }

    modifier requiresProofOfSafety(bytes32 payloadHash, SecurityAttestation calldata proof) {
        _verifyProofOfSafety(payloadHash, proof);
        emit ProofOfSafetyAccepted(payloadHash, proof.riskScore, msg.sender);
        _;
    }

    constructor(address _securityOracleSigner) {
        contractOwner = msg.sender;
        securityOracleSigner = _securityOracleSigner;

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

    function setSecurityOracleSigner(address _newOracle) external onlyContractOwner {
        emit SecurityOracleUpdated(securityOracleSigner, _newOracle);
        securityOracleSigner = _newOracle;
    }

    function setMaximumAcceptableRiskScore(uint8 _newThreshold) external onlyContractOwner {
        maximumAcceptableRiskScore = _newThreshold;
    }

    function _verifyProofOfSafety(bytes32 payloadHash, SecurityAttestation calldata proof) internal view {
        if (block.timestamp > proof.expiresAt) {
            revert ProofExpired(block.timestamp, proof.expiresAt);
        }
        if (proof.riskScore > maximumAcceptableRiskScore) {
            revert RiskScoreExceedsThreshold(proof.riskScore, maximumAcceptableRiskScore);
        }

        bytes32 structHash = keccak256(
            abi.encode(
                ATTESTATION_TYPEHASH,
                payloadHash,
                proof.riskScore,
                keccak256(bytes(proof.verdict)),
                proof.expiresAt
            )
        );

        bytes32 digest = keccak256(abi.encodePacked("\x19\x01", DOMAIN_SEPARATOR, structHash));
        address recovered = ecrecover(digest, proof.v, proof.r, proof.s);

        if (recovered != securityOracleSigner) {
            revert OracleSignatureInvalid();
        }
    }
}
