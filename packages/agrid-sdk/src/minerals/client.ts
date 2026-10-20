/**
 * minerals-oracle-x402 TypeScript Client
 * High-performance autonomous client for AI agents and LLM tool chains
 */

import {
  ClientConfig,
  VerificationResponse,
  LithiumVerifyInput,
  NickelVerifyInput,
  CobaltVerifyInput,
  CopperVerifyInput,
  SilverVerifyInput,
  TungstenVerifyInput,
  RareEarthsVerifyInput,
  NiobiumScandiumVerifyInput,
  TradeDealProposeInput,
  TradeDealDualSignInput,
  TradeDealAttestation,
  EscrowCalldataResponse,
  SupportedChain
} from './types.js';

export class MineralsOracleClient {
  private readonly baseUrl: string;
  private readonly apiKey?: string;
  private readonly vaultKey?: string;
  private readonly devBypass: boolean;
  private readonly timeoutMs: number;

  constructor(config: ClientConfig = {}) {
    this.baseUrl = config.baseUrl?.replace(/\/$/, '') || 'https://minerals-oracle-x402-7qxtp3324q-du.a.run.app';
    const env = (typeof globalThis !== 'undefined' ? (globalThis as any).process?.env : undefined) || {};
    this.apiKey = config.apiKey || env.ORACLE_API_KEY;
    this.vaultKey = config.vaultKey || env.ORACLE_VAULT_KEY;
    this.devBypass = config.devBypass ?? true;
    this.timeoutMs = config.timeoutMs ?? 15000;
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string>)
    };

    if (this.apiKey) {
      headers['X-API-Key'] = this.apiKey;
    }
    if (this.vaultKey) {
      headers['X-Agent-Vault-Key'] = this.vaultKey;
    }
    if (this.devBypass) {
      headers['X-Dev-Bypass'] = 'true';
    }

    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), this.timeoutMs);

    try {
      const response = await fetch(url, {
        ...options,
        headers,
        signal: controller.signal
      });

      if (!response.ok) {
        let errorBody = '';
        try {
          errorBody = await response.text();
        } catch (_) {}
        throw new Error(`MineralsOracle HTTP ${response.status} on ${endpoint}: ${errorBody}`);
      }

      return (await response.json()) as T;
    } finally {
      clearTimeout(timer);
    }
  }

  /**
   * Check Oracle node health & operational status
   */
  async getHealth(): Promise<Record<string, any>> {
    return this.request<Record<string, any>>('/health', { method: 'GET' });
  }

  /**
   * Verify Australian Spodumene to Lithium Hydroxide provenance
   */
  async verifyLithium(input: LithiumVerifyInput): Promise<VerificationResponse> {
    return this.request<VerificationResponse>('/api/v1/lithium/verify-origin', {
      method: 'POST',
      body: JSON.stringify(input)
    });
  }

  /**
   * Verify Indonesian Nickel MHP, SIMBARA NTPN tax & CBAM compliance
   */
  async verifyNickel(input: NickelVerifyInput): Promise<VerificationResponse> {
    return this.request<VerificationResponse>('/api/v1/nickel/verify-origin', {
      method: 'POST',
      body: JSON.stringify(input)
    });
  }

  /**
   * Verify DRC Cobalt Hydroxide CEEC seal & ILO child labor due diligence
   */
  async verifyCobalt(input: CobaltVerifyInput): Promise<VerificationResponse> {
    return this.request<VerificationResponse>('/api/v1/cobalt/verify-origin', {
      method: 'POST',
      body: JSON.stringify(input)
    });
  }

  /**
   * Verify Chilean/Peruvian Copper Cathode LME Grade A & HVDC cable standards
   */
  async verifyCopper(input: CopperVerifyInput): Promise<VerificationResponse> {
    return this.request<VerificationResponse>('/api/v1/copper/verify-origin', {
      method: 'POST',
      body: JSON.stringify(input)
    });
  }

  /**
   * Verify Mexican Silver Doré N-Type TOPCon Solar PV paste purity (>=99.99%)
   */
  async verifySilver(input: SilverVerifyInput): Promise<VerificationResponse> {
    return this.request<VerificationResponse>('/api/v1/silver/verify-origin', {
      method: 'POST',
      body: JSON.stringify(input)
    });
  }

  /**
   * Verify Western Tungsten APT (Almonty Sangdong / Bakuta) & US NDAA Sec 848 defense eligibility
   */
  async verifyTungsten(input: TungstenVerifyInput): Promise<VerificationResponse> {
    return this.request<VerificationResponse>('/api/v1/tungsten/verify-origin', {
      method: 'POST',
      body: JSON.stringify(input)
    });
  }

  /**
   * Verify Allied Rare Earths NdPr (Sarfartoq / Silmet) & China MOFCOM 0.1% Rule compliance
   */
  async verifyRareEarths(input: RareEarthsVerifyInput): Promise<VerificationResponse> {
    return this.request<VerificationResponse>('/api/v1/rare-earths/verify-origin', {
      method: 'POST',
      body: JSON.stringify(input)
    });
  }

  /**
   * Verify NioCorp Elk Creek Niobium (ASTM A550) & Scandium Oxide (Sc2O3 >=99.5%) defense standard
   */
  async verifyNiobiumScandium(input: NiobiumScandiumVerifyInput): Promise<VerificationResponse> {
    return this.request<VerificationResponse>('/api/v1/niobium-scandium/verify-origin', {
      method: 'POST',
      body: JSON.stringify(input)
    });
  }

  /**
   * Verify Composite EV Battery Passport (NCM 811 / 622) with multi-stream Merkle proof
   */
  async verifyCompositeBattery(payload: Record<string, any>): Promise<VerificationResponse> {
    return this.request<VerificationResponse>('/api/v1/battery/verify-composite-passport', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
  }

  /**
   * A2A Autonomous Trade: Seller proposes bilateral mineral agreement
   */
  async proposeTradeDeal(input: TradeDealProposeInput): Promise<TradeDealAttestation> {
    let payload: Record<string, any>;
    if (input.spec) {
      payload = {
        spec: input.spec,
        seller_signature: input.seller_signature
      };
    } else {
      const commodity = input.commodity || input.commodity_type || 'COPPER_CATHODE';
      const volumeTons = input.volume_tons ?? input.quantity_metric_tons ?? 100.0;
      const unitPrice = input.unit_price_usd_per_ton ?? input.unit_price_usd ?? 9000.0;
      const totalValue = input.total_deal_value_usd ?? (volumeTons * unitPrice);
      const dealId = input.deal_id || `DEAL-SDK-${Date.now()}`;
      const eblId = input.ebl_document_id || input.ebl_document_hash || `EBL-${dealId}`;
      const sellerAddr = input.seller_agent_address || '0x1111111111111111111111111111111111111111';
      const buyerAddr = input.buyer_agent_address || '0x2222222222222222222222222222222222222222';
      const createdAt = input.created_at_utc || new Date().toISOString();

      payload = {
        spec: {
          deal_id: dealId,
          commodity,
          volume_tons: volumeTons,
          unit_price_usd_per_ton: unitPrice,
          total_deal_value_usd: totalValue,
          origin_country: input.origin_country || 'CHL',
          destination_country: input.destination_country || 'USA',
          feoc_cleared: input.feoc_cleared ?? true,
          mass_balance_cleared: input.mass_balance_cleared ?? true,
          ebl_document_id: eblId,
          buyer_agent_address: buyerAddr,
          seller_agent_address: sellerAddr,
          settlement_currency: input.settlement_currency || 'USDC',
          projected_savings_usd: input.projected_savings_usd || 0.0,
          created_at_utc: createdAt
        },
        seller_signature: input.seller_signature
      };
    }

    return this.request<TradeDealAttestation>('/api/v1/a2a/deals/propose', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
  }

  /**
   * A2A Autonomous Trade: Buyer dual-signs agreement, triggering Oracle cryptographic seal
   */
  async dualSignTradeDeal(input: TradeDealDualSignInput): Promise<TradeDealAttestation> {
    const payload = {
      deal_id: input.deal_id,
      buyer_signature: input.buyer_signature,
      buyer_agent_address: input.buyer_agent_address || '0x2222222222222222222222222222222222222222'
    };
    return this.request<TradeDealAttestation>('/api/v1/a2a/deals/dual-sign', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
  }

  /**
   * Retrieve A2A deal state and attestation
   */
  async getTradeDeal(dealId: string): Promise<Record<string, any>> {
    return this.request<Record<string, any>>(`/api/v1/a2a/deals/${encodeURIComponent(dealId)}`, {
      method: 'GET'
    });
  }

  /**
   * Build live on-chain deposit calldata for Polygon, Base, Arbitrum, or Solana
   */
  async getEscrowCalldata(dealId: string, chain: SupportedChain = 'polygon'): Promise<EscrowCalldataResponse> {
    const data = await this.request<any>(
      `/api/v1/a2a/deals/${encodeURIComponent(dealId)}/escrow-calldata?chain=${chain}`,
      { method: 'GET' }
    );
    const chainIds: Record<SupportedChain, number> = {
      polygon: 137,
      base: 8453,
      arbitrum: 42161,
      solana: 501
    };
    return {
      chain,
      chain_id: data.chain_id || chainIds[chain] || 137,
      ...data
    };
  }

  /**
   * Fetch FastMCP Tool Specification schemas
   */
  async getMCPTools(): Promise<Record<string, any>> {
    return this.request<Record<string, any>>('/mcp/tools', { method: 'GET' });
  }

  /**
   * Harmonized Collaborator Flow: Single-call end-to-end autonomous trade execution
   */
  async harmonizeTradeFlow(input: Record<string, any>): Promise<Record<string, any>> {
    return this.request<Record<string, any>>('/api/v1/trade/harmonize-flow', {
      method: 'POST',
      body: JSON.stringify(input)
    });
  }
}
