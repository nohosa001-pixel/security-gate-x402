/**
 * A.GRID Multi-Chain Verified Contract Registry & Specifications
 */

export interface ChainConfig {
  chainId: number;
  name: string;
  currency: string;
  agentEscrowAddress: string;
  securityGateGuardAddress: string;
  explorerUrl: string;
  rpcUrl: string;
  iconClass: string;
}

export const SUPPORTED_CHAINS: Record<number, ChainConfig> = {
  137: {
    chainId: 137,
    name: 'Polygon Mainnet',
    currency: 'MATIC / USDC',
    agentEscrowAddress: '0x8ACafCEce0B1BFE140e75614b90FD1307b6f389d',
    securityGateGuardAddress: '0x5cC5Afa2a97599d492A3E408Fdd95fD0b520f173',
    explorerUrl: 'https://polygonscan.com',
    rpcUrl: 'https://polygon-rpc.com',
    iconClass: 'polygon'
  },
  8453: {
    chainId: 8453,
    name: 'Base Mainnet',
    currency: 'ETH / USDC',
    agentEscrowAddress: '0x99FEd65Cf2D5378182c3481B300124BB1a8Ad278',
    securityGateGuardAddress: '0x306e69E59E5bCEa769C6CeA76A79AFA8f2A5F408',
    explorerUrl: 'https://basescan.org',
    rpcUrl: 'https://mainnet.base.org',
    iconClass: 'base'
  },
  42161: {
    chainId: 42161,
    name: 'Arbitrum One',
    currency: 'ETH / USDC',
    agentEscrowAddress: '0x99FEd65Cf2D5378182c3481B300124BB1a8Ad278',
    securityGateGuardAddress: '0x306e69E59E5bCEa769C6CeA76A79AFA8f2A5F408',
    explorerUrl: 'https://arbiscan.io',
    rpcUrl: 'https://arb1.arbitrum.io/rpc',
    iconClass: 'arbitrum'
  }
};

export const ORACLE_PUBLIC_KEY = '0x255F9991233f86B29dB847c8d5b8CB9915e80dCf';
export const PROTOCOL_TOLL_BPS = 25; // 0.25%
export const SLASHING_BOUNTY_BPS = 2000; // 20% to treasury, 80% to client
