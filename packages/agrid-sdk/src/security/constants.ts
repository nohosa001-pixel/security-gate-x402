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
		agenticShieldPool: string;
		logisticsPoDEscrow: string;
	};
	tokens: {
		usdc: string;
	};
	oracleSigner: string;
}

export const OFFICIAL_ORACLE_SIGNER =
	"0xA185B43fDD19619f99952AAed6eabf1029bF36a1";

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
			safeSecurityGateGuard: "0x4f747fae13AeF51b7F9523157c6be70Ba3B6Cb55",
			agentCreditOracle: "0x402E95B6aE9BBD26A227A1AE2aC7f52E14E1A314",
			agentComplianceRegistry: "0x984C25Ff74fE9bAb094D1F60085b0Ced8eA0f2e9",
			agentEscrow: "0x5501083317AdA8f7CA3456EC8F8773d37dc59b1e",
			agentInsurancePool: "0xD067DF08B2ee8C1B5a38d17C1C443C233249dE90",
			agentLendingPool: "0x269aa749743C5B3C3d4787fB3c947B7e6c29bfa4",
			agentFactoringPool: "0xeE7Dd9b20676109F0d0288B903faba2F7135C44a",
			agentTreasuryVault: "0x29fB5a06Fd9bF59703eA1B07546bBE9AB60E6019",
			securityGateConsumer: "0x4a8B283C755fe3EC1c3f77d78d43c82a173a68aB",
			agenticShieldPool: "0x0343e9Fff9451346767D6cca2C249d82667E7dE0",
			logisticsPoDEscrow: "0x95df688E42C3053a1f09A46F179A8250bEAB40aB",
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
			safeSecurityGateGuard: "0x5F565115441188b5dCa06539615Fc154BC7f3028",
			agentCreditOracle: "0xd1F37196A1fe73Caa89ce7f4a58D6Fe49FD47655",
			agentComplianceRegistry: "0x4693a3644ac4E215Bed9ADb841212D4ee83D0675",
			agentEscrow: "0x5eE3C093D8D473670A5F67306d75316123A019a9",
			agentInsurancePool: "0x4f747fae13AeF51b7F9523157c6be70Ba3B6Cb55",
			agentLendingPool: "0x402E95B6aE9BBD26A227A1AE2aC7f52E14E1A314",
			agentFactoringPool: "0x984C25Ff74fE9bAb094D1F60085b0Ced8eA0f2e9",
			agentTreasuryVault: "0x5501083317AdA8f7CA3456EC8F8773d37dc59b1e",
			securityGateConsumer: "0xD067DF08B2ee8C1B5a38d17C1C443C233249dE90",
			agenticShieldPool: "0x7F14ed4F8C08ee694b4f143144bb8cC51BF4A1AE",
			logisticsPoDEscrow: "0x0343e9Fff9451346767D6cca2C249d82667E7dE0",
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
			safeSecurityGateGuard: "0x7F14ed4F8C08ee694b4f143144bb8cC51BF4A1AE",
			agentCreditOracle: "0x0343e9Fff9451346767D6cca2C249d82667E7dE0",
			agentComplianceRegistry: "0x95df688E42C3053a1f09A46F179A8250bEAB40aB",
			agentEscrow: "0x8eB40eF1f032dd66CD54c6e1D0C29980C31d5E57",
			agentInsurancePool: "0x984C25Ff74fE9bAb094D1F60085b0Ced8eA0f2e9",
			agentLendingPool: "0xbFc79F55E410508aBCa2FF8ebA1120de4F209f68",
			agentFactoringPool: "0x5F565115441188b5dCa06539615Fc154BC7f3028",
			agentTreasuryVault: "0xd1F37196A1fe73Caa89ce7f4a58D6Fe49FD47655",
			securityGateConsumer: "0x4693a3644ac4E215Bed9ADb841212D4ee83D0675",
			agenticShieldPool: "0xAAde57ABf49A52bC2981Ff64dc54dE27d8c8Ac28",
			logisticsPoDEscrow: "0x3A863A2b1018B47FE79041FCDF56efEa3f8b978F",
		},
		tokens: {
			usdc: "0xaf88d065e77c8cC2239327C5EDb3A432268e5831",
		},
		oracleSigner: OFFICIAL_ORACLE_SIGNER,
	},
};

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

export function isChainSupported(chainId: number): boolean {
	return chainId in SECURITY_GATE_REGISTRY;
}
