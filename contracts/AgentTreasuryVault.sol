// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface IERC20 {
    function transferFrom(address sender, address recipient, uint256 amount) external returns (bool);
    function transfer(address recipient, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
}

/**
 * @title AgentTreasuryVault
 * @notice Autonomous AI Agent Hedge Fund & Treasury Vault Protocol.
 *         Allows investors and DAOs to pool capital (USDC) into a yield-generating vault
 *         managed by high-credit autonomous AI agents.
 *         Strict security: NO trade or capital allocation can occur without an
 *         EIP-712 cryptographic TradeAuthorization signature from the Security Gate Oracle.
 */
contract AgentTreasuryVault {
    IERC20 public immutable usdcToken;
    address public oracleSigner;
    address public oracleTreasury;
    address public owner;

    uint256 public totalAssets;               // Total underlying USDC assets in vault
    uint256 public totalShares;               // Total LP vault shares issued
    uint256 public totalCumulativeProfits;    // Historical realized profit generated
    uint256 public highWaterMark;             // Peak vault share price for performance fee tracking

    uint256 public constant MANAGER_FEE_BPS = 1500;  // 15.0% performance fee to AI Agent
    uint256 public constant ORACLE_FEE_BPS = 500;    // 5.0% performance fee to Oracle Treasury
    uint256 public constant BPS_DENOMINATOR = 10000;

    struct TradeAuthorization {
        uint256 strategyId;
        address agent;
        address targetProtocol;
        uint256 maxAllocation;
        uint256 maxSlippageBps;
        bytes32 strategyHash;
        uint256 expiresAt;
        uint256 nonce;
        uint8 v;
        bytes32 r;
        bytes32 s;
    }

    bytes32 public constant EIP712_DOMAIN_TYPEHASH = keccak256(
        "EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)"
    );

    bytes32 public constant TRADE_AUTHORIZATION_TYPEHASH = keccak256(
        "TradeAuthorization(uint256 strategyId,address agent,address targetProtocol,uint256 maxAllocation,uint256 maxSlippageBps,bytes32 strategyHash,uint256 expiresAt,uint256 nonce)"
    );

    bytes32 public immutable DOMAIN_SEPARATOR;

    mapping(address => uint256) public shares;
    mapping(uint256 => bool) public executedNonces;
    mapping(address => bool) public whitelistedProtocols;

    // Events
    event Deposited(address indexed caller, address indexed receiver, uint256 assets, uint256 sharesMinted);
    event Withdrawn(address indexed caller, address indexed receiver, uint256 assets, uint256 sharesBurned);
    event StrategyExecuted(uint256 indexed strategyId, address indexed agent, address indexed target, uint256 allocation);
    event ProfitsDistributed(uint256 grossProfit, uint256 managerFee, uint256 oracleFee, uint256 netProfitToPool);
    event ProtocolWhitelisted(address indexed protocol, bool status);
    event OracleSignerUpdated(address indexed oldSigner, address indexed newSigner);

    // Errors
    error Unauthorized();
    error InvalidOracleSignature();
    error AuthorizationExpired();
    error TargetNotWhitelisted();
    error AllocationExceedsBalance();
    error NonceAlreadyUsed();
    error TransferFailed();
    error ZeroAmount();

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
                keccak256(bytes("AgentTreasuryVault")),
                keccak256(bytes("1.0.0")),
                block.chainid,
                address(this)
            )
        );
    }

    // --- Investor Vault Deposit & Withdrawal ---

    function deposit(uint256 assets, address receiver) external returns (uint256) {
        if (assets == 0) revert ZeroAmount();
        if (!usdcToken.transferFrom(msg.sender, address(this), assets)) revert TransferFailed();

        uint256 sharesToMint;
        if (totalShares == 0 || totalAssets == 0) {
            sharesToMint = assets; // 1:1 initial share ratio
        } else {
            sharesToMint = (assets * totalShares) / totalAssets;
        }

        shares[receiver] += sharesToMint;
        totalShares += sharesToMint;
        totalAssets += assets;

        emit Deposited(msg.sender, receiver, assets, sharesToMint);
        return sharesToMint;
    }

    function withdraw(uint256 sharesToBurn, address receiver) external returns (uint256) {
        if (sharesToBurn == 0 || shares[msg.sender] < sharesToBurn) revert ZeroAmount();

        uint256 assetsOut = (sharesToBurn * totalAssets) / totalShares;
        if (usdcToken.balanceOf(address(this)) < assetsOut) revert AllocationExceedsBalance();

        shares[msg.sender] -= sharesToBurn;
        totalShares -= sharesToBurn;
        totalAssets -= assetsOut;

        if (!usdcToken.transfer(receiver, assetsOut)) revert TransferFailed();

        emit Withdrawn(msg.sender, receiver, assetsOut, sharesToBurn);
        return assetsOut;
    }

    // --- AI Strategy Execution with Cryptographic Oracle Guard ---

    function executeStrategy(
        TradeAuthorization calldata auth,
        bytes calldata callData
    ) external returns (bytes memory) {
        if (block.timestamp > auth.expiresAt) revert AuthorizationExpired();
        if (executedNonces[auth.nonce]) revert NonceAlreadyUsed();
        if (!whitelistedProtocols[auth.targetProtocol]) revert TargetNotWhitelisted();
        if (usdcToken.balanceOf(address(this)) < auth.maxAllocation) revert AllocationExceedsBalance();

        executedNonces[auth.nonce] = true;

        // Verify Security Gate Oracle Signature
        bytes32 structHash = keccak256(
            abi.encode(
                TRADE_AUTHORIZATION_TYPEHASH,
                auth.strategyId,
                auth.agent,
                auth.targetProtocol,
                auth.maxAllocation,
                auth.maxSlippageBps,
                auth.strategyHash,
                auth.expiresAt,
                auth.nonce
            )
        );

        bytes32 digest = keccak256(abi.encodePacked("\x19\x01", DOMAIN_SEPARATOR, structHash));
        address recovered = ecrecover(digest, auth.v, auth.r, auth.s);
        if (recovered != oracleSigner) revert InvalidOracleSignature();

        // Disburse allocation to whitelisted target protocol
        if (auth.maxAllocation > 0) {
            if (!usdcToken.transfer(auth.targetProtocol, auth.maxAllocation)) revert TransferFailed();
        }

        // Low-level call if callData present
        bytes memory returnData;
        if (callData.length > 0) {
            (bool success, bytes memory res) = auth.targetProtocol.call(callData);
            if (!success) revert TransferFailed();
            returnData = res;
        }

        emit StrategyExecuted(auth.strategyId, auth.agent, auth.targetProtocol, auth.maxAllocation);
        return returnData;
    }

    // --- Performance Fee Distribution ---

    function recordProfitsAndDistributeFees(
        uint256 grossProfit,
        address managerAgent
    ) external returns (uint256 netProfit) {
        if (grossProfit == 0) revert ZeroAmount();
        if (!usdcToken.transferFrom(msg.sender, address(this), grossProfit)) revert TransferFailed();

        uint256 managerFee = (grossProfit * MANAGER_FEE_BPS) / BPS_DENOMINATOR; // 15%
        uint256 oracleFee = (grossProfit * ORACLE_FEE_BPS) / BPS_DENOMINATOR;   // 5%
        netProfit = grossProfit - managerFee - oracleFee;                        // 80% to LPs

        // Pay AI manager performance reward
        if (managerFee > 0 && managerAgent != address(0)) {
            if (!usdcToken.transfer(managerAgent, managerFee)) revert TransferFailed();
        }

        // Pay Oracle protocol guard fee
        if (oracleFee > 0 && oracleTreasury != address(0)) {
            if (!usdcToken.transfer(oracleTreasury, oracleFee)) revert TransferFailed();
        }

        totalAssets += netProfit;
        totalCumulativeProfits += grossProfit;

        emit ProfitsDistributed(grossProfit, managerFee, oracleFee, netProfit);
        return netProfit;
    }

    // --- Admin & Whitelist ---

    function setProtocolWhitelist(address protocol, bool status) external onlyOwner {
        whitelistedProtocols[protocol] = status;
        emit ProtocolWhitelisted(protocol, status);
    }

    function setOracleSigner(address _newSigner) external onlyOwner {
        emit OracleSignerUpdated(oracleSigner, _newSigner);
        oracleSigner = _newSigner;
    }

    function getVaultMetrics() external view returns (
        uint256 assets,
        uint256 sharesTotal,
        uint256 cumulativeProfits,
        uint256 sharePriceUsdc
    ) {
        uint256 price = totalShares == 0 ? 1e6 : (totalAssets * 1e6) / totalShares;
        return (totalAssets, totalShares, totalCumulativeProfits, price);
    }
}
