// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface IERC20 {
    function transferFrom(address sender, address recipient, uint256 amount) external returns (bool);
    function transfer(address recipient, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
}

interface IAgentCreditOracle {
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

    function isEligibleForLoan(
        address agent,
        uint256 requestedAmountUsdc,
        CreditCertificate calldata cert
    ) external view returns (bool);
}

/**
 * @title AgentLendingPool
 * @notice Autonomous Uncollateralized Micro-Lending Pool for AI Agents.
 *         Allows qualified autonomous agents to borrow operational capital (for task stakes,
 *         API calls, or DeFi gas) without collateral, based on AgentCreditOracle EIP-712 certificates.
 */
contract AgentLendingPool {
    IERC20 public immutable usdcToken;
    IAgentCreditOracle public creditOracle;
    address public owner;

    uint256 public totalLiquidity;
    uint256 public totalBorrowed;
    uint256 public constant ANNUAL_INTEREST_BPS = 500; // 5.0% annual interest
    uint256 public constant MIN_LOAN_FEE_BPS = 50;     // 0.5% minimum origination fee

    struct Loan {
        uint256 loanId;
        address borrower;
        uint256 principal;
        uint256 interestFee;
        uint256 totalDue;
        uint256 borrowedAt;
        uint256 dueDate;
        bool isRepaid;
        bool isDefaulted;
    }

    uint256 private _nextLoanId = 1;
    mapping(uint256 => Loan) public loans;
    mapping(address => uint256[]) private _agentLoans;
    mapping(address => uint256) public lpBalances;

    // Events
    event LiquidityDeposited(address indexed provider, uint256 amount);
    event LiquidityWithdrawn(address indexed provider, uint256 amount);
    event LoanDisbursed(uint256 indexed loanId, address indexed borrower, uint256 principal, uint256 totalDue, uint256 dueDate);
    event LoanRepaid(uint256 indexed loanId, address indexed borrower, uint256 amountRepaid);
    event LoanDefaulted(uint256 indexed loanId, address indexed borrower, uint256 unpaidAmount);
    event CreditOracleUpdated(address indexed oldOracle, address indexed newOracle);

    // Errors
    error Unauthorized();
    error InsufficientPoolLiquidity();
    error LoanAlreadyClosed();
    error LoanNotDueYet();
    error TransferFailed();
    error IneligibleForCredit();

    modifier onlyOwner() {
        if (msg.sender != owner) revert Unauthorized();
        _;
    }

    constructor(address _usdcToken, address _creditOracle) {
        owner = msg.sender;
        usdcToken = IERC20(_usdcToken);
        creditOracle = IAgentCreditOracle(_creditOracle);
    }

    function setCreditOracle(address _newOracle) external onlyOwner {
        emit CreditOracleUpdated(address(creditOracle), _newOracle);
        creditOracle = IAgentCreditOracle(_newOracle);
    }

    /**
     * @notice Liquidity providers deposit USDC to earn interest from agent loans.
     */
    function depositLiquidity(uint256 amount) external {
        if (!usdcToken.transferFrom(msg.sender, address(this), amount)) revert TransferFailed();
        lpBalances[msg.sender] += amount;
        totalLiquidity += amount;
        emit LiquidityDeposited(msg.sender, amount);
    }

    /**
     * @notice Liquidity providers withdraw their USDC capital and accrued earnings.
     */
    function withdrawLiquidity(uint256 amount) external {
        if (lpBalances[msg.sender] < amount) revert Unauthorized();
        uint256 availableLiquidity = usdcToken.balanceOf(address(this));
        if (amount > availableLiquidity) revert InsufficientPoolLiquidity();

        lpBalances[msg.sender] -= amount;
        totalLiquidity -= amount;
        if (!usdcToken.transfer(msg.sender, amount)) revert TransferFailed();

        emit LiquidityWithdrawn(msg.sender, amount);
    }

    /**
     * @notice Autonomous Agent borrows uncollateralized USDC by presenting an EIP-712 credit certificate.
     */
    function borrowWithCredit(
        uint256 amount,
        uint256 durationDays,
        IAgentCreditOracle.CreditCertificate calldata cert
    ) external returns (uint256) {
        // 1. Verify credit eligibility via AgentCreditOracle
        if (!creditOracle.isEligibleForLoan(msg.sender, amount, cert)) {
            revert IneligibleForCredit();
        }

        // 2. Check pool liquidity
        uint256 availableLiquidity = usdcToken.balanceOf(address(this));
        if (amount > availableLiquidity) revert InsufficientPoolLiquidity();

        // 3. Compute interest fee (max of 0.5% min fee or pro-rated 5% APY)
        uint256 interestFee = (amount * ANNUAL_INTEREST_BPS * durationDays) / (365 * 10000);
        uint256 minFee = (amount * MIN_LOAN_FEE_BPS) / 10000;
        if (interestFee < minFee) {
            interestFee = minFee;
        }

        uint256 totalDue = amount + interestFee;
        uint256 dueDate = block.timestamp + (durationDays * 1 days);
        uint256 loanId = _nextLoanId++;

        loans[loanId] = Loan({
            loanId: loanId,
            borrower: msg.sender,
            principal: amount,
            interestFee: interestFee,
            totalDue: totalDue,
            borrowedAt: block.timestamp,
            dueDate: dueDate,
            isRepaid: false,
            isDefaulted: false
        });

        _agentLoans[msg.sender].push(loanId);
        totalBorrowed += amount;

        // Disburse loan to agent
        if (!usdcToken.transfer(msg.sender, amount)) revert TransferFailed();

        emit LoanDisbursed(loanId, msg.sender, amount, totalDue, dueDate);
        return loanId;
    }

    /**
     * @notice Agent repays outstanding loan with interest, improving on-chain credit history.
     */
    function repayLoan(uint256 loanId) external {
        Loan storage loan = loans[loanId];
        if (loan.isRepaid || loan.isDefaulted) revert LoanAlreadyClosed();

        if (!usdcToken.transferFrom(msg.sender, address(this), loan.totalDue)) revert TransferFailed();

        loan.isRepaid = true;
        totalBorrowed -= loan.principal;
        totalLiquidity += loan.interestFee; // Interest accrues to pool LPs

        emit LoanRepaid(loanId, loan.borrower, loan.totalDue);
    }

    /**
     * @notice Liquidates and flags a loan as defaulted if unpaid past the due date.
     */
    function liquidateDefaultedLoan(uint256 loanId) external {
        Loan storage loan = loans[loanId];
        if (loan.isRepaid || loan.isDefaulted) revert LoanAlreadyClosed();
        if (block.timestamp <= loan.dueDate) revert LoanNotDueYet();

        loan.isDefaulted = true;
        totalBorrowed -= loan.principal;

        emit LoanDefaulted(loanId, loan.borrower, loan.totalDue);
    }

    function getAgentLoans(address agent) external view returns (uint256[] memory) {
        return _agentLoans[agent];
    }
}
