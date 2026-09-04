// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface IERC20 {
    function transferFrom(address sender, address recipient, uint256 amount) external returns (bool);
    function transfer(address recipient, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
}

/**
 * @title AgentFactoringPool
 * @notice Autonomous AI Agent Receivables Factoring & Short-Term Bond Protocol.
 *         Enables AI agents to immediately discount and liquidate pending escrow
 *         milestone payments (invoices) for operational liquidity.
 *         Investor LPs earn high annualized short-term bond yields, backed by
 *         Security Gate Oracle's EIP-712 credit attestations.
 */
contract AgentFactoringPool {
    IERC20 public immutable usdcToken;
    address public oracleSigner;
    address public oracleTreasury;
    address public owner;

    uint256 public totalLiquidity;            // Available investor LP capital
    uint256 public totalFactoredVolume;       // Cumulative face value factored
    uint256 public totalYieldEarned;          // Realized discount profits for LPs
    uint256 public activeAdvanceLiabilities;  // Outstanding advance capital deployed

    struct Bond {
        uint256 invoiceId;
        uint256 escrowJobId;
        address agent;
        uint256 faceValue;
        uint256 advanceAmount;
        uint256 discountFee;
        uint256 oracleFee;
        uint256 issuedAt;
        uint256 maturityDate;
        bool isSettled;
    }

    struct FactoringAttestation {
        uint256 invoiceId;
        uint256 escrowJobId;
        address agent;
        uint256 faceValue;
        uint256 discountRateBps;
        uint256 oracleFee;
        uint256 maturityDate;
        uint256 expiresAt;
        uint256 nonce;
        uint8 v;
        bytes32 r;
        bytes32 s;
    }

    bytes32 public constant EIP712_DOMAIN_TYPEHASH = keccak256(
        "EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)"
    );

    bytes32 public constant FACTORING_ATTESTATION_TYPEHASH = keccak256(
        "FactoringAttestation(uint256 invoiceId,uint256 escrowJobId,address agent,uint256 faceValue,uint256 discountRateBps,uint256 oracleFee,uint256 maturityDate,uint256 expiresAt,uint256 nonce)"
    );

    bytes32 public immutable DOMAIN_SEPARATOR;

    mapping(uint256 => Bond) public bonds;
    mapping(address => uint256[]) private _agentBonds;
    mapping(address => uint256) public lpBalances;
    mapping(uint256 => bool) public executedNonces;

    // Events
    event LiquidityDeposited(address indexed lp, uint256 amount);
    event LiquidityWithdrawn(address indexed lp, uint256 amount);
    event BondPurchased(
        uint256 indexed invoiceId,
        uint256 indexed escrowJobId,
        address indexed agent,
        uint256 faceValue,
        uint256 advanceAmount,
        uint256 discountFee,
        uint256 maturityDate
    );
    event InvoiceSettled(uint256 indexed invoiceId, uint256 amountSettled, uint256 realizedProfit);
    event OracleSignerUpdated(address indexed oldSigner, address indexed newSigner);

    // Errors
    error Unauthorized();
    error InvalidSignature();
    error AttestationExpired();
    error InsufficientPoolLiquidity();
    error NonceAlreadyUsed();
    error BondAlreadyExists();
    error BondNotFoundOrSettled();
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
                keccak256(bytes("AgentFactoringPool")),
                keccak256(bytes("1.0.0")),
                block.chainid,
                address(this)
            )
        );
    }

    // --- LP Liquidity Operations ---

    function depositLiquidity(uint256 amount) external {
        if (amount == 0) revert TransferFailed();
        if (!usdcToken.transferFrom(msg.sender, address(this), amount)) revert TransferFailed();

        lpBalances[msg.sender] += amount;
        totalLiquidity += amount;

        emit LiquidityDeposited(msg.sender, amount);
    }

    function withdrawLiquidity(uint256 amount) external {
        if (lpBalances[msg.sender] < amount) revert TransferFailed();
        if (usdcToken.balanceOf(address(this)) < amount) revert InsufficientPoolLiquidity();

        lpBalances[msg.sender] -= amount;
        totalLiquidity -= amount;

        if (!usdcToken.transfer(msg.sender, amount)) revert TransferFailed();

        emit LiquidityWithdrawn(msg.sender, amount);
    }

    // --- Receivables Bond Factoring ---

    function purchaseReceivableBond(FactoringAttestation calldata att) external returns (uint256) {
        if (block.timestamp > att.expiresAt) revert AttestationExpired();
        if (executedNonces[att.nonce]) revert NonceAlreadyUsed();
        if (bonds[att.invoiceId].invoiceId != 0) revert BondAlreadyExists();

        executedNonces[att.nonce] = true;

        // Verify Oracle Signature over FactoringAttestation
        bytes32 structHash = keccak256(
            abi.encode(
                FACTORING_ATTESTATION_TYPEHASH,
                att.invoiceId,
                att.escrowJobId,
                att.agent,
                att.faceValue,
                att.discountRateBps,
                att.oracleFee,
                att.maturityDate,
                att.expiresAt,
                att.nonce
            )
        );

        bytes32 digest = keccak256(abi.encodePacked("\x19\x01", DOMAIN_SEPARATOR, structHash));
        address recovered = ecrecover(digest, att.v, att.r, att.s);
        if (recovered != oracleSigner) revert InvalidSignature();

        // Calculate discount fee and advance capital
        uint256 discountFee = (att.faceValue * att.discountRateBps) / 10000;
        uint256 advanceAmount = att.faceValue - discountFee - att.oracleFee;

        if (usdcToken.balanceOf(address(this)) < (advanceAmount + att.oracleFee)) {
            revert InsufficientPoolLiquidity();
        }

        // Register Bond
        bonds[att.invoiceId] = Bond({
            invoiceId: att.invoiceId,
            escrowJobId: att.escrowJobId,
            agent: att.agent,
            faceValue: att.faceValue,
            advanceAmount: advanceAmount,
            discountFee: discountFee,
            oracleFee: att.oracleFee,
            issuedAt: block.timestamp,
            maturityDate: att.maturityDate,
            isSettled: false
        });

        _agentBonds[att.agent].push(att.invoiceId);
        activeAdvanceLiabilities += advanceAmount;
        totalFactoredVolume += att.faceValue;

        // Disburse advance to agent immediately
        if (!usdcToken.transfer(att.agent, advanceAmount)) revert TransferFailed();

        // Disburse risk-free fee to Oracle Treasury
        if (att.oracleFee > 0) {
            if (!usdcToken.transfer(oracleTreasury, att.oracleFee)) revert TransferFailed();
        }

        emit BondPurchased(
            att.invoiceId,
            att.escrowJobId,
            att.agent,
            att.faceValue,
            advanceAmount,
            discountFee,
            att.maturityDate
        );

        return advanceAmount;
    }

    // --- Invoice Settlement (from Escrow or Direct Payer) ---

    function settleInvoice(uint256 invoiceId) external {
        Bond storage bond = bonds[invoiceId];
        if (bond.invoiceId == 0 || bond.isSettled) revert BondNotFoundOrSettled();

        // Transfer the full face value into this pool
        if (!usdcToken.transferFrom(msg.sender, address(this), bond.faceValue)) revert TransferFailed();

        bond.isSettled = true;
        if (activeAdvanceLiabilities >= bond.advanceAmount) {
            activeAdvanceLiabilities -= bond.advanceAmount;
        }

        totalYieldEarned += bond.discountFee;
        totalLiquidity += bond.discountFee; // Yield permanently enhances LP liquidity pool value

        emit InvoiceSettled(invoiceId, bond.faceValue, bond.discountFee);
    }

    // --- Views ---

    function getBond(uint256 invoiceId) external view returns (Bond memory) {
        return bonds[invoiceId];
    }

    function getAgentBonds(address agent) external view returns (uint256[] memory) {
        return _agentBonds[agent];
    }

    function getPoolMetrics() external view returns (
        uint256 poolLiquidity,
        uint256 cumulativeVolume,
        uint256 realizedYield,
        uint256 activeLiabilities
    ) {
        return (totalLiquidity, totalFactoredVolume, totalYieldEarned, activeAdvanceLiabilities);
    }

    function setOracleSigner(address _newSigner) external onlyOwner {
        emit OracleSignerUpdated(oracleSigner, _newSigner);
        oracleSigner = _newSigner;
    }
}
