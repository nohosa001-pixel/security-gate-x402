/**
 * minerals-oracle-x402 TypeScript SDK Data Schemas
 * Pure Autonomous AI Agent (M2M) Critical Minerals Provenance & Multi-Chain Escrow Protocol
 */

export type MineralType =
  | 'LITHIUM_HYDROXIDE'
  | 'LITHIUM_CARBONATE'
  | 'NICKEL_MHP'
  | 'COBALT_HYDROXIDE'
  | 'COPPER_CATHODE'
  | 'COPPER_CONCENTRATE'
  | 'SILVER_DORE'
  | 'SILVER_POWDER_SOLAR_PV'
  | 'NATURAL_GRAPHITE'
  | 'SYNTHETIC_GRAPHITE'
  | 'MANGANESE_SULFATE'
  | 'NEODYMIUM_DYSPROSIUM'
  | 'ANTIMONY_TRIOXIDE'
  | 'TUNGSTEN_APT'
  | 'TUNGSTEN_SCRAP'
  | 'RARE_EARTHS_NDPR'
  | 'FERRONIOBIUM'
  | 'SCANDIUM_OXIDE'
  | 'RECYCLED_BLACK_MASS'
  | 'LITHIUM_BLACK_MASS'
  | 'NICKEL_COBALT_BLACK_MASS';

export type SourceCountry =
  | 'AUS'
  | 'IDN'
  | 'COD'
  | 'CHL'
  | 'ARG'
  | 'PER'
  | 'MEX'
  | 'KOR'
  | 'USA'
  | 'CAN'
  | 'PRT'
  | 'AGO'
  | 'GRL'
  | 'EST'
  | 'KAZ'
  | 'BRA'
  | 'ZMB'
  | 'ESP'
  | 'ZAF'
  | 'CHN'
  | 'DEU'
  | 'VNM';

export type SupportedChain = 'polygon' | 'base' | 'arbitrum' | 'solana';

export interface ClientConfig {
  baseUrl?: string;
  apiKey?: string;
  vaultKey?: string;
  devBypass?: boolean;
  timeoutMs?: number;
}

export interface VerificationVerdict {
  is_compliant: boolean;
  status: string;
  confidence_score: number;
  reasons: string[];
  [key: string]: any;
}

export interface VerificationResponse<T = VerificationVerdict> {
  status: 'success' | 'error';
  batch_id?: string;
  trace_id?: string;
  lot_id?: string;
  audit_verdict?: T;
  verdict?: T;
  proof_hash?: string;
  onchain_signature?: string;
  timestamp?: string;
  [key: string]: any;
}

export interface LithiumVerifyInput {
  trace_id: string;
  product?: string;
  mine_name: string;
  mine_country?: string;
  coordinates: [number, number];
  minedex_tenement_id?: string;
  spodumene_tonnage_extracted: number;
  spodumene_grade_pct?: number;
  refinery_facility: string;
  refinery_country?: string;
  refined_output_tonnage: number;
  refinery_feoc_equity_pct?: number;
}

export interface NickelVerifyInput {
  trace_id: string;
  product?: string;
  concession_name: string;
  coordinates: [number, number];
  simbara_ntpn?: string;
  limonite_ore_input_tons: number;
  ore_grade_ni_pct?: number;
  hpal_refinery_name: string;
  mhp_output_tons: number;
  mhp_grade_ni_pct?: number;
  captive_coal_power?: boolean;
  feoc_equity_pct?: number;
}

export interface CobaltVerifyInput {
  trace_id: string;
  product?: string;
  concession_name: string;
  province?: string;
  coordinates: [number, number];
  mine_type?: 'LSM' | 'ASM';
  ceec_seal_id?: string;
  asm_comingled?: boolean;
  zero_child_labor_audit_ref?: string | null;
  heterogenite_ore_input_tons: number;
  ore_grade_co_pct?: number;
  refinery_name: string;
  refinery_country?: string;
  cobalt_hydroxide_output_tons: number;
  hydroxide_grade_co_pct?: number;
  feoc_equity_pct?: number;
}

export interface CopperVerifyInput {
  lot_id: string;
  mine_concession_name: string;
  extraction_coordinates: [number, number];
  source_country?: string;
  feedstock_concentrate_tons: number;
  concentrate_grade_cu_pct?: number;
  sulfuric_acid_input_tons?: number;
  refined_copper_cathode_tons: number;
  copper_cathode_purity_pct?: number;
  cochilco_export_clearance_id?: string | null;
  hvdc_cable_spec_compliant?: boolean;
  feoc_shareholding_pct?: number;
}

export interface SilverVerifyInput {
  lot_id: string;
  mine_concession_name: string;
  extraction_coordinates: [number, number];
  source_country?: string;
  feedstock_dore_or_ore_kg: number;
  feedstock_silver_grade_pct?: number;
  refined_solar_powder_kg: number;
  refined_purity_pct?: number;
  lbma_good_delivery_ref?: string | null;
  conflict_free_asm_verified?: boolean;
  topcon_pv_grade_compliant?: boolean;
  feoc_shareholding_pct?: number;
}

export interface TungstenVerifyInput {
  batch_id: string;
  tenement_id: string;
  latitude: number;
  longitude: number;
  apt_wo3_grade_pct?: number;
  dodd_frank_conflict_free?: boolean;
  ndaa_defense_procurement_eligible?: boolean;
  source_country?: SourceCountry;
  client_identity?: string;
}

export interface RareEarthsVerifyInput {
  batch_id: string;
  tenement_id: string;
  latitude: number;
  longitude: number;
  ndpr_oxide_purity_pct?: number;
  thorium_uranium_radiation_ppm?: number;
  declared_china_origin_ratio?: number;
  source_country?: SourceCountry;
  client_identity?: string;
}

export interface NiobiumScandiumVerifyInput {
  batch_id: string;
  tenement_id: string;
  latitude: number;
  longitude: number;
  commodity_type?: 'FERRONIOBIUM' | 'SCANDIUM_OXIDE';
  fe_nb_grade_pct?: number;
  sc2o3_purity_pct?: number;
  doe_exim_loan_eligible?: boolean;
  ndaa_defense_procurement_eligible?: boolean;
  source_country?: SourceCountry;
  client_identity?: string;
}

export interface TradeDealSpec {
  deal_id: string;
  commodity: MineralType;
  volume_tons: number;
  unit_price_usd_per_ton: number;
  total_deal_value_usd: number;
  origin_country: SourceCountry | string;
  destination_country: string;
  feoc_cleared?: boolean;
  mass_balance_cleared?: boolean;
  ebl_document_id: string;
  buyer_agent_address: string;
  seller_agent_address: string;
  settlement_currency?: string;
  projected_savings_usd?: number;
  gain_share_rate_pct?: number;
  calculated_gain_share_fee_usd?: number;
  fee_cap_applied?: boolean;
  hybrid_settlement_summary?: string;
  expires_at_utc?: string;
  created_at_utc: string;
}

export interface TradeDealProposeInput {
  spec?: TradeDealSpec;
  seller_signature: string;
  deal_id?: string;
  commodity?: MineralType;
  commodity_type?: MineralType;
  volume_tons?: number;
  quantity_metric_tons?: number;
  unit_price_usd_per_ton?: number;
  unit_price_usd?: number;
  total_deal_value_usd?: number;
  origin_country?: SourceCountry | string;
  destination_country?: string;
  feoc_cleared?: boolean;
  mass_balance_cleared?: boolean;
  ebl_document_id?: string;
  ebl_document_hash?: string;
  buyer_agent_address?: string;
  seller_agent_address?: string;
  delivery_incoterm?: string;
  settlement_currency?: string;
  projected_savings_usd?: number;
  created_at_utc?: string;
  [key: string]: any;
}

export interface TradeDealDualSignInput {
  deal_id: string;
  buyer_signature: string;
  buyer_agent_address?: string;
}

export interface TradeDealAttestation {
  status: string;
  deal_id: string;
  deal_state: string;
  buyer_agent_address: string;
  seller_agent_address: string;
  total_value_usd: number;
  oracle_signature?: string;
  deal_hash: string;
  verified_at_utc: string;
  [key: string]: any;
}

export interface EscrowCalldataResponse {
  deal_id: string;
  chain: string;
  chain_id: number;
  escrow_contract_address: string;
  usdc_token_address: string;
  total_usd_value: number;
  required_usdc_units: string;
  seller_agent_address: string;
  buyer_agent_address: string;
  deal_id_bytes32: string;
  ebl_hash_bytes32: string;
  duration_seconds: number;
  function_signature: string;
  calldata: string;
  next_action: string;
}
