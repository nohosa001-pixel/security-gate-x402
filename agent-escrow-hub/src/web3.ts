/**
 * A.GRID Native Web3 Provider & Contract Dispatcher
 * Directly interacts with EIP-1193 wallet providers (MetaMask, Rabby, Coinbase Wallet)
 * without heavy dependency bloat.
 */

import { SUPPORTED_CHAINS } from './contracts.ts';

declare global {
  interface Window {
    ethereum?: any;
  }
}

export class Web3Manager {
  private currentAccount: string | null = null;
  private currentChainId: number = 137;

  constructor() {
    this.initListeners();
  }

  private initListeners() {
    if (typeof window !== 'undefined' && window.ethereum) {
      window.ethereum.on('accountsChanged', (accounts: string[]) => {
        this.currentAccount = accounts.length > 0 ? accounts[0] : null;
        window.dispatchEvent(new CustomEvent('wallet_changed', { detail: { account: this.currentAccount } }));
      });

      window.ethereum.on('chainChanged', (hexChainId: string) => {
        this.currentChainId = parseInt(hexChainId, 16);
        window.dispatchEvent(new CustomEvent('chain_changed', { detail: { chainId: this.currentChainId } }));
      });
    }
  }

  isWalletAvailable(): boolean {
    return typeof window !== 'undefined' && typeof window.ethereum !== 'undefined';
  }

  async connectWallet(): Promise<string> {
    if (!this.isWalletAvailable()) {
      throw new Error('No Web3 wallet detected. Please install MetaMask, Rabby, or Coinbase Wallet.');
    }

    const accounts = await window.ethereum.request({ method: 'eth_requestAccounts' });
    if (!accounts || accounts.length === 0) {
      throw new Error('User rejected wallet connection.');
    }

    this.currentAccount = accounts[0];
    const hexChainId = await window.ethereum.request({ method: 'eth_chainId' });
    this.currentChainId = parseInt(hexChainId, 16);

    return this.currentAccount as string;
  }

  disconnectWallet() {
    this.currentAccount = null;
  }

  getAccount(): string | null {
    return this.currentAccount;
  }

  getChainId(): number {
    return this.currentChainId;
  }

  async switchChain(targetChainId: number): Promise<void> {
    if (!this.isWalletAvailable()) return;

    const hexChainId = '0x' + targetChainId.toString(16);
    try {
      await window.ethereum.request({
        method: 'wallet_switchEthereumChain',
        params: [{ chainId: hexChainId }]
      });
      this.currentChainId = targetChainId;
    } catch (switchError: any) {
      // Error code 4902 means the chain has not been added to MetaMask
      if (switchError.code === 4902) {
        const config = SUPPORTED_CHAINS[targetChainId];
        if (config) {
          await window.ethereum.request({
            method: 'wallet_addEthereumChain',
            params: [{
              chainId: hexChainId,
              chainName: config.name,
              rpcUrls: [config.rpcUrl],
              blockExplorerUrls: [config.explorerUrl],
              nativeCurrency: {
                name: config.currency.split(' / ')[0],
                symbol: config.currency.split(' / ')[0],
                decimals: 18
              }
            }]
          });
          this.currentChainId = targetChainId;
        }
      } else {
        throw switchError;
      }
    }
  }

  /**
   * Helper to ABI-encode a 32-byte word (address, uint, or bytes32)
   */
  private pad32(val: string | number | bigint): string {
    if (typeof val === 'number' || typeof val === 'bigint') {
      return BigInt(val).toString(16).padStart(64, '0');
    }
    const clean = val.replace(/^0x/, '');
    return clean.padStart(64, '0');
  }

  /**
   * Dispatches createJob on AgentEscrow contract
   */
  async createJobOnChain(params: {
    worker: string;
    payoutUSDC: number;
    stakeUSDC: number;
    specHash: string;
    durationSeconds: number;
  }): Promise<string> {
    const config = SUPPORTED_CHAINS[this.currentChainId] || SUPPORTED_CHAINS[137];
    const contractAddress = config.agentEscrowAddress;

    const payoutUnits = BigInt(Math.round(params.payoutUSDC * 1e6));
    const stakeUnits = BigInt(Math.round(params.stakeUSDC * 1e6));
    const duration = BigInt(params.durationSeconds);
    const workerAddr = params.worker.startsWith('0x') ? params.worker : '0x0000000000000000000000000000000000000000';

    const calldata = '0x1cb96927' +
      this.pad32(workerAddr) +
      this.pad32(payoutUnits) +
      this.pad32(stakeUnits) +
      this.pad32(params.specHash) +
      this.pad32(duration);

    return this.sendTransaction({
      to: contractAddress,
      data: calldata
    });
  }

  /**
   * Dispatches depositStake on AgentEscrow contract (selector: 0xcb82cc8f)
   */
  async stakeJobOnChain(jobId: number): Promise<string> {
    const config = SUPPORTED_CHAINS[this.currentChainId] || SUPPORTED_CHAINS[137];
    const contractAddress = config.agentEscrowAddress;

    // depositStake(uint256) selector: 0xcb82cc8f
    const calldata = '0xcb82cc8f' + this.pad32(jobId);

    return this.sendTransaction({
      to: contractAddress,
      data: calldata
    });
  }

  /**
   * Submits on-chain settlement (completeJob or slashJob) with EIP-712 attestation proof
   */
  async settleJobOnChain(params: {
    jobId: number;
    isSlash: boolean;
    attestation: {
      jobId: number;
      deliverableHash: string;
      riskScore: number;
      verdict: string;
      expiresAt: number;
      v?: number;
      r?: string;
      s?: string;
    }
  }): Promise<string> {
    const config = SUPPORTED_CHAINS[this.currentChainId] || SUPPORTED_CHAINS[137];
    const contractAddress = config.agentEscrowAddress;
    const selector = params.isSlash ? '0x80fa0b1a' : '0x122969ae';

    const jobIdHex = this.pad32(params.jobId);
    const tupleOffset = this.pad32(64); // 0x40 offset for tuple
    
    const attJobId = this.pad32(params.attestation.jobId);
    const attDelivHash = this.pad32(params.attestation.deliverableHash);
    const attRisk = this.pad32(params.attestation.riskScore);
    const stringOffset = this.pad32(8 * 32); // offset after 8 words = 256 bytes
    const attExpires = this.pad32(params.attestation.expiresAt);
    const attV = this.pad32(params.attestation.v ?? 27);
    const attR = this.pad32(params.attestation.r ?? '0x0');
    const attS = this.pad32(params.attestation.s ?? '0x0');

    const verdictStr = params.attestation.verdict || (params.isSlash ? 'BLOCKED' : 'PASSED');
    const strLen = this.pad32(verdictStr.length);
    const strHex = Array.from(verdictStr).map(c => c.charCodeAt(0).toString(16).padStart(2, '0')).join('').padEnd(64, '0');

    const calldata = selector +
      jobIdHex +
      tupleOffset +
      attJobId +
      attDelivHash +
      attRisk +
      stringOffset +
      attExpires +
      attV +
      attR +
      attS +
      strLen +
      strHex;

    return this.sendTransaction({
      to: contractAddress,
      data: calldata
    });
  }

  /**
   * Dispatches a real on-chain transaction or falls back to simulation mode
   */
  async sendTransaction(params: { to: string; data?: string; value?: string }): Promise<string> {
    if (!this.isWalletAvailable() || !this.currentAccount) {
      // Generate a simulated transaction hash
      const simTx = '0x' + Array.from({ length: 64 }, () => Math.floor(Math.random() * 16).toString(16)).join('');
      return simTx;
    }

    const txHash = await window.ethereum.request({
      method: 'eth_sendTransaction',
      params: [{
        from: this.currentAccount,
        to: params.to,
        data: params.data || '0x',
        value: params.value || '0x0'
      }]
    });

    return txHash;
  }
}

export const web3Manager = new Web3Manager();
