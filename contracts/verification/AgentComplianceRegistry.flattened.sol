// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title AgentComplianceRegistry
 * @notice On-chain EU AI Act (Articles 50 & 53) Regulatory Compliance Verification Registry.
 *         Ensures that enterprise smart contracts only interact with AI agents holding an active,
 *         cryptographically certified compliance passport.
 */
contract AgentComplianceRegistry {
    address public complianceOracleSigner;
    address public owner;

    struct CompliancePassport {
        address agentAddress;
        string passportId;
        bool isCertified;
        uint256 expiresAt;
        uint8 v;
        bytes32 r;
        bytes32 s;
    }

    bytes32 public constant EIP712_DOMAIN_TYPEHASH = keccak256(
        "EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)"
    );

    bytes32 public constant COMPLIANCE_PASSPORT_TYPEHASH = keccak256(
        "CompliancePassport(address agentAddress,string passportId,bool isCertified,uint256 expiresAt)"
    );

    bytes32 public immutable DOMAIN_SEPARATOR;

    event ComplianceOracleUpdated(address indexed oldSigner, address indexed newSigner);
    event ComplianceVerified(address indexed agent, string passportId, bool isCertified);

    error InvalidOracleSignature();
    error PassportExpired();
    error AgentNotCertified();
    error AgentAddressMismatch();
    error Unauthorized();

    modifier onlyOwner() {
        if (msg.sender != owner) revert Unauthorized();
        _;
    }

    constructor(address _complianceOracleSigner) {
        owner = msg.sender;
        complianceOracleSigner = _complianceOracleSigner;

        DOMAIN_SEPARATOR = keccak256(
            abi.encode(
                EIP712_DOMAIN_TYPEHASH,
                keccak256(bytes("AgentComplianceRegistry")),
                keccak256(bytes("1.0.0")),
                block.chainid,
                address(0)
            )
        );
    }

    function setComplianceOracleSigner(address _newSigner) external onlyOwner {
        emit ComplianceOracleUpdated(complianceOracleSigner, _newSigner);
        complianceOracleSigner = _newSigner;
    }

    /**
     * @notice Verifies an agent's EU AI Act compliance passport.
     */
    function verifyPassport(CompliancePassport calldata passport) public view returns (bool) {
        if (block.timestamp > passport.expiresAt) revert PassportExpired();
        if (!passport.isCertified) revert AgentNotCertified();

        bytes32 structHash = keccak256(
            abi.encode(
                COMPLIANCE_PASSPORT_TYPEHASH,
                passport.agentAddress,
                keccak256(bytes(passport.passportId)),
                passport.isCertified,
                passport.expiresAt
            )
        );

        bytes32 digest = keccak256(abi.encodePacked("\x19\x01", DOMAIN_SEPARATOR, structHash));
        address recovered = ecrecover(digest, passport.v, passport.r, passport.s);

        if (recovered != complianceOracleSigner) revert InvalidOracleSignature();
        return true;
    }

    /**
     * @notice Enforces that a caller or counterparty agent is fully compliant with EU AI Act.
     */
    function requireCompliance(address agent, CompliancePassport calldata passport) external view returns (bool) {
        if (passport.agentAddress != agent) revert AgentAddressMismatch();
        return verifyPassport(passport);
    }
}
