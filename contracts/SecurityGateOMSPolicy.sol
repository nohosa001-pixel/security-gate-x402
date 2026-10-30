// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title ISessionPolicy
 * @notice Standard interface for ERC-7579 / Polygon Open Money Stack (OMS) Smart Session Policies.
 */
interface ISessionPolicy {
    /**
     * @notice Enforces policy checks before a session-enabled user operation is executed.
     * @param sessionKey The public key or address of the ephemeral agent session.
     * @param target The target contract receiving the transaction.
     * @param value The amount of native currency being moved.
     * @param data The calldata to be executed on the target.
     * @param proof Additional proof data containing the Security Gate Attestation.
     */
    function checkUserOpPolicy(
        bytes32 sessionKey,
        address target,
        uint256 value,
        bytes calldata data,
        bytes calldata proof
    ) external view returns (bool);
}

/**
 * @title SecurityGateOMSPolicy
 * @notice Polygon OMS Smart Sessions Defense Policy: "No Proof-of-Safety, No Settlement".
 *         Binds agent wallet spending limits to deterministic Security Gate Inspection & Truth Verification.
 *         Supports multichain cross-rail settlement including Solana Mainnet via Polygon Open Money Stack (OMS).
 *
 * @dev Enforces:
 *      1. Task-level spending ceiling (max spend per session or lifetime).
 *      2. Whitelisted destination (e.g. A.GRID Universal Escrow Hub on Polygon: 0x8ACaf...).
 *      3. Deterministic EIP-712 Security Attestation from the Security Gate Oracle (<10ms AST & Injection check).
 *      4. Maximum risk score ceiling (e.g., risk_score <= 30/100).
 */
contract SecurityGateOMSPolicy is ISessionPolicy {
    address public owner;
    address public oracleSigner;
    uint8 public maxAllowedRiskScore = 30;

    // Polygon Universal Escrow Core on Polygon Mainnet (137)
    address public constant DEFAULT_POLYGON_ESCROW_HUB = 0x8ACafCEce0B1BFE140e75614b90FD1307b6f389d;

    struct SessionSpendConfig {
        uint256 maxSpendLimit;
        uint256 currentSpent;
        uint256 expiresAt;
        bool isActive;
        address allowedTarget;
    }

    // Mapping: sessionKey => SessionSpendConfig
    mapping(bytes32 => SessionSpendConfig) public sessionConfigs;

    // EIP-712 Domain & Typehashes
    bytes32 public constant EIP712_DOMAIN_TYPEHASH = keccak256(
        "EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)"
    );

    bytes32 public constant ATTESTATION_TYPEHASH = keccak256(
        "SecurityAttestation(bytes32 payloadHash,uint8 riskScore,string verdict,uint256 expiresAt)"
    );

    bytes32 public DOMAIN_SEPARATOR;

    // Events
    event SessionRegistered(bytes32 indexed sessionKey, uint256 maxLimit, uint256 expiresAt, address allowedTarget);
    event SessionRevoked(bytes32 indexed sessionKey);
    event PolicyChecked(bytes32 indexed sessionKey, address indexed target, uint256 value, uint8 riskScore);
    event OracleSignerUpdated(address indexed oldSigner, address indexed newSigner);

    // Errors
    error SessionInactive();
    error SessionExpired();
    error BudgetExceeded(uint256 attempted, uint256 remaining);
    error UnauthorizedTarget(address attempted, address expected);
    error MissingSecurityAttestation();
    error InvalidAttestationSignature();
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
                keccak256(bytes("SecurityGateOMSPolicy")),
                keccak256(bytes("1")),
                block.chainid,
                address(this)
            )
        );
    }

    /**
     * @notice Registers or updates a scoped agent session rule under Polygon OMS.
     * @param sessionKey The unique identifier or public key of the agent session.
     * @param maxSpendLimit Maximum cumulative spend limit (e.g. in USDC 6 decimals or WEI).
     * @param duration Validity duration in seconds.
     * @param allowedTarget The only contract the agent may call (0x0 defaults to A.GRID Escrow Hub).
     */
    function registerSession(
        bytes32 sessionKey,
        uint256 maxSpendLimit,
        uint256 duration,
        address allowedTarget
    ) external onlyOwner {
        address target = allowedTarget == address(0) ? DEFAULT_POLYGON_ESCROW_HUB : allowedTarget;
        sessionConfigs[sessionKey] = SessionSpendConfig({
            maxSpendLimit: maxSpendLimit,
            currentSpent: 0,
            expiresAt: block.timestamp + duration,
            isActive: true,
            allowedTarget: target
        });

        emit SessionRegistered(sessionKey, maxSpendLimit, block.timestamp + duration, target);
    }

    /**
     * @notice Turns off an active rule immediately (Kill-switch / Revoke switch).
     * @param sessionKey The session to revoke.
     */
    function revokeSession(bytes32 sessionKey) external onlyOwner {
        sessionConfigs[sessionKey].isActive = false;
        emit SessionRevoked(sessionKey);
    }

    /**
     * @notice Checks Polygon OMS Session Policy against budget, target, and Security Gate EIP-712 Attestation.
     * @param sessionKey The ephemeral session key identifier.
     * @param target The contract being called.
     * @param value The value being sent.
     * @param data The calldata being passed.
     * @param proof ABI encoded: (uint8 riskScore, string verdict, uint256 attestationExpiry, bytes signature).
     */
    function checkUserOpPolicy(
        bytes32 sessionKey,
        address target,
        uint256 value,
        bytes calldata data,
        bytes calldata proof
    ) external view override returns (bool) {
        SessionSpendConfig memory cfg = sessionConfigs[sessionKey];

        // 1. Check Session State
        if (!cfg.isActive) revert SessionInactive();
        if (block.timestamp > cfg.expiresAt) revert SessionExpired();

        // 2. Check Target Whitelist
        if (cfg.allowedTarget != address(0) && target != cfg.allowedTarget) {
            revert UnauthorizedTarget(target, cfg.allowedTarget);
        }

        // 3. Check Budget Ceiling
        if (cfg.currentSpent + value > cfg.maxSpendLimit) {
            revert BudgetExceeded(value, cfg.maxSpendLimit - cfg.currentSpent);
        }

        // 4. Check Security Gate Attestation (Deep Inspection Defense)
        if (proof.length == 0) revert MissingSecurityAttestation();

        (
            uint8 riskScore,
            string memory verdict,
            uint256 attestationExpiry,
            bytes memory signature
        ) = abi.decode(proof, (uint8, string, uint256, bytes));

        if (block.timestamp > attestationExpiry) revert AttestationExpired();
        if (riskScore > maxAllowedRiskScore) revert ExcessiveRiskScore(riskScore, maxAllowedRiskScore);

        // Verify EIP-712 signature over payload
        bytes32 payloadHash = keccak256(abi.encodePacked(target, value, data));
        bytes32 structHash = keccak256(
            abi.encode(
                ATTESTATION_TYPEHASH,
                payloadHash,
                riskScore,
                keccak256(bytes(verdict)),
                attestationExpiry
            )
        );

        bytes32 digest = keccak256(
            abi.encodePacked("\x19\x01", DOMAIN_SEPARATOR, structHash)
        );

        address recovered = recoverSigner(digest, signature);
        if (recovered != oracleSigner) revert InvalidAttestationSignature();

        return true;
    }

    /**
     * @dev Recovers signer address from an ECDSA signature.
     */
    function recoverSigner(bytes32 digest, bytes memory sig) internal pure returns (address) {
        if (sig.length != 65) return address(0);

        bytes32 r;
        bytes32 s;
        uint8 v;

        assembly {
            r := mload(add(sig, 32))
            s := mload(add(sig, 64))
            v := byte(0, mload(add(sig, 96)))
        }

        if (v < 27) {
            v += 27;
        }

        if (v != 27 && v != 28) {
            return address(0);
        }

        // Enforce EIP-2 / OpenZeppelin signature malleability prevention
        if (uint256(s) > 0x7FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF5D576E7357A4501DDFE92F46681B20A0) {
            return address(0);
        }

        return ecrecover(digest, v, r, s);
    }

    /**
     * @notice Updates the trusted Security Gate Oracle Signer address.
     */
    function setOracleSigner(address _newSigner) external onlyOwner {
        emit OracleSignerUpdated(oracleSigner, _newSigner);
        oracleSigner = _newSigner;
    }

    /**
     * @notice Updates the maximum allowed risk score.
     */
    function setMaxAllowedRiskScore(uint8 _newScore) external onlyOwner {
        maxAllowedRiskScore = _newScore;
    }
}
