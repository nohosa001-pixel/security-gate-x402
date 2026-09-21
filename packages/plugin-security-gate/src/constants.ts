/**
 * 🛡️ Security Gate x402 - Multi-Chain Contract Registry & Constants
 *
 * Fully deployed, verified, and operational smart contract addresses across:
 * - Polygon Mainnet (Chain ID 137)
 * - Base Mainnet (Chain ID 8453)
 * - Arbitrum One Mainnet (Chain ID 42161)
 */

export interface SecurityGateContractAddresses {
	chainId: number;
	chainName: string;
	explorerUrl: string;
	contracts: {
		safeSecurityGateGuard: string;
		agentCreditOracle: string;
		agentComplianceRegistry: string;
		agentEscrow: string;
		agentInsurancePool: string;
		agentLendingPool: string;
		agentFactoringPool: string;
		agentTreasuryVault: string;
		securityGateConsumer: string;
	};
	tokens: {
		usdc: string;
	};
	oracleSigner: string;
}

export const OFFICIAL_ORACLE_SIGNER =
	"0x255F9991233f86B29dB847c8d5b8CB9915e80dCf";

export const SECURITY_GATE_REGISTRY: Record<
	number,
	SecurityGateContractAddresses
> = {
	// 1. Polygon Mainnet
	137: {
		chainId: 137,
		chainName: "Polygon Mainnet",
		explorerUrl: "https://polygonscan.com",
		contracts: {
			safeSecurityGateGuard: "0x5cC5Afa2a97599d492A3E408Fdd95fD0b520f173",
			agentCreditOracle: "0x6418f408cFf03F862D7691f01fAb00a895E6aB93",
			agentComplianceRegistry: "0x28292D76E07E5539F15F3b97935dE8E0432E76DD",
			agentEscrow: "0x8ACafCEce0B1BFE140e75614b90FD1307b6f389d",
			agentInsurancePool: "0xE67F4BC75B11dBb3ef2C9Ad1848B4b193c2c69C6",
			agentLendingPool: "0xe43a9C368808B2dfF139D27789C40A3C8F2282cF",
			agentFactoringPool: "0xd0Aa4Aed2AeDE14611B53C3e93CF784F3Fe05BB0",
			agentTreasuryVault: "0xfCf3BF5fB5858db9aE81bE458B39b0032fc0C638",
			securityGateConsumer: "0x9E3dEE18D8139E1d20f9f7D1F6673c75727F1DDA",
		},
		tokens: {
			usdc: "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359",
		},
		oracleSigner: OFFICIAL_ORACLE_SIGNER,
	},

	// 2. Base Mainnet
	8453: {
		chainId: 8453,
		chainName: "Base Mainnet",
		explorerUrl: "https://basescan.org",
		contracts: {
			safeSecurityGateGuard: "0x306e69E59E5bCEa769C6CeA76A79AFA8f2A5F408",
			agentCreditOracle: "0x227e1129Ba9B39a50fb9E0802bA13A7F77Debe93",
			agentComplianceRegistry: "0x821d88Df97F6063a32fDff85FBad9784B9B7292D",
			agentEscrow: "0x99FEd65Cf2D5378182c3481B300124BB1a8Ad278",
			agentInsurancePool: "0x90308AedEe6430D11e5214cf9d2F563333D33Ef2",
			agentLendingPool: "0x5cC5Afa2a97599d492A3E408Fdd95fD0b520f173",
			agentFactoringPool: "0x6418f408cFf03F862D7691f01fAb00a895E6aB93",
			agentTreasuryVault: "0xF8e1439F61c9F2d5FdbA382D524FabB35e12ae55",
			securityGateConsumer: "0xdC6Cb774d51681Fcbba0E67Ca677dEc5705aaB35",
		},
		tokens: {
			usdc: "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
		},
		oracleSigner: OFFICIAL_ORACLE_SIGNER,
	},

	// 3. Arbitrum One Mainnet
	42161: {
		chainId: 42161,
		chainName: "Arbitrum One",
		explorerUrl: "https://arbiscan.io",
		contracts: {
			safeSecurityGateGuard: "0x306e69E59E5bCEa769C6CeA76A79AFA8f2A5F408",
			agentCreditOracle: "0x227e1129Ba9B39a50fb9E0802bA13A7F77Debe93",
			agentComplianceRegistry: "0x821d88Df97F6063a32fDff85FBad9784B9B7292D",
			agentEscrow: "0x99FEd65Cf2D5378182c3481B300124BB1a8Ad278",
			agentInsurancePool: "0x90308AedEe6430D11e5214cf9d2F563333D33Ef2",
			agentLendingPool: "0x5cC5Afa2a97599d492A3E408Fdd95fD0b520f173",
			agentFactoringPool: "0x6418f408cFf03F862D7691f01fAb00a895E6aB93",
			agentTreasuryVault: "0xF8e1439F61c9F2d5FdbA382D524FabB35e12ae55",
			securityGateConsumer: "0xdC6Cb774d51681Fcbba0E67Ca677dEc5705aaB35",
		},
		tokens: {
			usdc: "0xaf88d065e77c8cC2239327C5EDb3A432268e5831",
		},
		oracleSigner: OFFICIAL_ORACLE_SIGNER,
	},
};

/**
 * Retrieves verified Security Gate contracts for a given chainId.
 * Defaults to Polygon (137) if chain is not explicitly specified.
 */
export function getSecurityGateContracts(
	chainId: number = 137,
): SecurityGateContractAddresses {
	const config = SECURITY_GATE_REGISTRY[chainId];
	if (!config) {
		throw new Error(
			`Unsupported Chain ID: ${chainId}. Supported chains: ${Object.keys(
				SECURITY_GATE_REGISTRY,
			).join(", ")}`,
		);
	}
	return config;
}

/**
 * Checks if a blockchain network is supported by Security Gate x402
 */
export function isChainSupported(chainId: number): boolean {
	return chainId in SECURITY_GATE_REGISTRY;
}
