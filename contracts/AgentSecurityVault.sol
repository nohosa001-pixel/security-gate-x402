// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface IERC20 {
    function transferFrom(address sender, address recipient, uint256 amount) external returns (bool);
    function transfer(address recipient, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
}

/**
 * @title AgentSecurityVault
 * @notice Pre-funded USDC vault for autonomous agents settling x402 security inspection fees.
 */
contract AgentSecurityVault {
    IERC20 public immutable usdcToken;
    address public gateTreasury;
    address public owner;

    mapping(address => uint256) public agentBalances;

    event Deposited(address indexed agent, uint256 amount);
    event Withdrawn(address indexed agent, uint256 amount);
    event FeeDeducted(address indexed agent, uint256 amount);

    error InsufficientBalance();
    error TransferFailed();
    error Unauthorized();

    modifier onlyOwner() {
        if (msg.sender != owner) revert Unauthorized();
        _;
    }

    modifier onlyTreasury() {
        if (msg.sender != gateTreasury && msg.sender != owner) revert Unauthorized();
        _;
    }

    constructor(address _usdcToken, address _gateTreasury) {
        owner = msg.sender;
        usdcToken = IERC20(_usdcToken);
        gateTreasury = _gateTreasury;
    }

    function deposit(uint256 amount) external {
        if (!usdcToken.transferFrom(msg.sender, address(this), amount)) revert TransferFailed();
        agentBalances[msg.sender] += amount;
        emit Deposited(msg.sender, amount);
    }

    function withdraw(uint256 amount) external {
        if (agentBalances[msg.sender] < amount) revert InsufficientBalance();
        agentBalances[msg.sender] -= amount;
        if (!usdcToken.transfer(msg.sender, amount)) revert TransferFailed();
        emit Withdrawn(msg.sender, amount);
    }

    function settleFee(address agent, uint256 amount) external onlyTreasury {
        if (agentBalances[agent] < amount) revert InsufficientBalance();
        agentBalances[agent] -= amount;
        if (!usdcToken.transfer(gateTreasury, amount)) revert TransferFailed();
        emit FeeDeducted(agent, amount);
    }
}
