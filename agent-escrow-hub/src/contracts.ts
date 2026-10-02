/**
 * A.GRID Multi-Chain Verified Contract Registry & Specifications
 */

export interface ChainConfig {
  chainId: number;
  name: string;
  currency: string;
  agentEscrowAddress: string;
  universalEscrowCoreAddress: string;
  truthAdapterAddress: string;
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
    universalEscrowCoreAddress: '0x4Dbd77F4799816859a595f24a57A786516D2EAa8',
    truthAdapterAddress: '0xCDE0edBE56Ae24D99F57eDacFB860a8c76f0856e',
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
    universalEscrowCoreAddress: '0x745F7FAfFdb626B931Fe769476a09125cbf9d94b',
    truthAdapterAddress: '0x2BAd02A09524Bf449c49C56A594BDAe942a1fFE6',
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
    universalEscrowCoreAddress: '0x745F7FAfFdb626B931Fe769476a09125cbf9d94b',
    truthAdapterAddress: '0x2BAd02A09524Bf449c49C56A594BDAe942a1fFE6',
    securityGateGuardAddress: '0x306e69E59E5bCEa769C6CeA76A79AFA8f2A5F408',
    explorerUrl: 'https://arbiscan.io',
    rpcUrl: 'https://arb1.arbitrum.io/rpc',
    iconClass: 'arbitrum'
  },
  501: {
    chainId: 501,
    name: 'Solana Mainnet',
    currency: 'SOL / SPL USDC',
    agentEscrowAddress: 'AGR3W3R9pKxnuZGYrpaggfkbMKVrjoniLaGvi1voBFSC',
    universalEscrowCoreAddress: 'AGR3W3R9pKxnuZGYrpaggfkbMKVrjoniLaGvi1voBFSC',
    truthAdapterAddress: 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v', // SPL USDC Mint
    securityGateGuardAddress: '411ksMz9RHYVtVMe6RUUErzZYtrU9zzvkgzswKbqx9qp',
    explorerUrl: 'https://solscan.io',
    rpcUrl: 'https://api.mainnet-beta.solana.com',
    iconClass: 'solana'
  }
};

export const SOLANA_ESCROW_PROGRAM_ID = 'AGR3W3R9pKxnuZGYrpaggfkbMKVrjoniLaGvi1voBFSC';
export const SOLANA_USDC_MINT = 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v';
export const SOLANA_TREASURY_PUBKEY = '411ksMz9RHYVtVMe6RUUErzZYtrU9zzvkgzswKbqx9qp';

export const ORACLE_PUBLIC_KEY = '0xA185B43fDD19619f99952AAed6eabf1029bF36a1';
export const PROTOCOL_TOLL_BPS = 25; // 0.25%
export const SLASHING_BOUNTY_BPS = 2000; // 20% to treasury, 80% to client
