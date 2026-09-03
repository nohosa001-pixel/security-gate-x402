// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title AgentCreditOracle
 * @notice On-chain Credit Rating Verification Oracle for Autonomous AI Agents ("Moody's & S&P of AI Agents").
 *         Enables uncollateralized lending, credit lines, and flash loan risk limits on EVM chains.
 */
contract AgentCreditOracle {
    address public oracleSigner;
    address public owner;

    struct CreditCertificate {
        address agentAddress;
        uint16 creditScore;
        string grade;
        uint256 maxCreditLimitUsdc;
        uint256 expiresAt;
        uint8 v;
        bytes32 r;
        bytes32 s;
    }

    bytes32 public constant EIP712_DOMAIN_TYPEHASH = keccak256(
        "EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)"
    );

    bytes32 public constant CREDIT_CERTIFICATE_TYPEHASH = keccak256(
        "CreditCertificate(address agentAddress,uint16 creditScore,string grade,uint256 maxCreditLimitUsdc,uint256 expiresAt)"
    );

    bytes32 public immutable DOMAIN_SEPARATOR;

    event CreditOracleSignerUpdated(address indexed oldSigner, address indexed newSigner);
    event CreditVerified(address indexed agent, uint16 score, string grade, uint256 maxCreditLimit);

    error InvalidOracleSignature();
    error CertificateExpired();
    error AgentAddressMismatch();
    error IneligibleForCredit(uint256 requested, uint256 maxAllowed);
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
                keccak256(bytes("AgentCreditRatingOracle")),
                keccak256(bytes("1.0.0")),
                block.chainid,
                address(0)
            )
        );
    }

    function setOracleSigner(address _newSigner) external onlyOwner {
        emit CreditOracleSignerUpdated(oracleSigner, _newSigner);
        oracleSigner = _newSigner;
    }

    /**
     * @notice Verifies an agent's EIP-712 credit certificate.
     */
    function verifyCertificate(CreditCertificate calldata cert) public view returns (bool) {
        if (block.timestamp > cert.expiresAt) revert CertificateExpired();

        bytes32 structHash = keccak256(
            abi.encode(
                CREDIT_CERTIFICATE_TYPEHASH,
                cert.agentAddress,
                cert.creditScore,
                keccak256(bytes(cert.grade)),
                cert.maxCreditLimitUsdc,
                cert.expiresAt
            )
        );

        bytes32 digest = keccak256(abi.encodePacked("\x19\x01", DOMAIN_SEPARATOR, structHash));
        address recovered = ecrecover(digest, cert.v, cert.r, cert.s);

        if (recovered != oracleSigner) revert InvalidOracleSignature();
        return true;
    }

    /**
     * @notice Hook for DeFi lending pools: checks whether an agent qualifies for an uncollateralized loan amount.
     */
    function isEligibleForLoan(
        address agent,
        uint256 requestedAmountUsdc,
        CreditCertificate calldata cert
    ) external view returns (bool) {
        if (cert.agentAddress != agent) revert AgentAddressMismatch();
        verifyCertificate(cert);

        if (requestedAmountUsdc > cert.maxCreditLimitUsdc) {
            revert IneligibleForCredit(requestedAmountUsdc, cert.maxCreditLimitUsdc);
        }
        return true;
    }
}
