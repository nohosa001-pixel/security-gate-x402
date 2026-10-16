-- ==============================================================================
-- DUNE ANALYTICS SQL QUERIES: Security-Gate-x402 & A.GRID Protocol
-- Networks: Base Mainnet (8453) & Polygon PoS (137)
-- Engine: DuneSQL (Trino)
-- ==============================================================================

-- ==============================================================================
-- QUERY 1: Total Value Shielded (TVS) & Cumulative Volume (Base + Polygon)
-- Description: Measures total USDC settled across UniversalEscrowCore and micro-batches.
-- ==============================================================================
WITH settlements AS (
    -- 1. Base Mainnet Direct Settlements
    SELECT 
        block_time,
        'Base' as network,
        bytearray_to_uint256(bytearray_substring(data, 1, 32)) / 1e6 AS volume_usdc,
        bytearray_to_uint256(bytearray_substring(data, 33, 32)) / 1e6 AS protocol_fee_usdc
    FROM base.logs
    WHERE contract_address = 0x99FEd65Cf2D5378182c3481B300124BB1a8Ad278 -- UniversalEscrowCore Base
      AND topic0 = 0x5a1768417935cf9135fc522bf0da7c688849b251a37c1992797e937d2f349141 -- DirectSettlementExecuted
    
    UNION ALL

    -- 2. Polygon Mainnet Direct Settlements
    SELECT 
        block_time,
        'Polygon' as network,
        bytearray_to_uint256(bytearray_substring(data, 1, 32)) / 1e6 AS volume_usdc,
        bytearray_to_uint256(bytearray_substring(data, 33, 32)) / 1e6 AS protocol_fee_usdc
    FROM polygon.logs
    WHERE contract_address = 0x8ACafCEce0B1BFE140e75614b90FD1307b6f389d -- UniversalEscrowCore Polygon
      AND topic0 = 0x5a1768417935cf9135fc522bf0da7c688849b251a37c1992797e937d2f349141 -- DirectSettlementExecuted
)
SELECT 
    date_trunc('day', block_time) AS date,
    network,
    COUNT(*) AS daily_settlements,
    SUM(volume_usdc) AS daily_volume_usdc,
    SUM(SUM(volume_usdc)) OVER (PARTITION BY network ORDER BY date_trunc('day', block_time)) AS cumulative_volume_usdc,
    SUM(protocol_fee_usdc) AS daily_protocol_fees_usdc,
    SUM(SUM(protocol_fee_usdc)) OVER (PARTITION BY network ORDER BY date_trunc('day', block_time)) AS cumulative_protocol_fees_usdc
FROM settlements
GROUP BY 1, 2
ORDER BY 1 DESC, 2;


-- ==============================================================================
-- QUERY 2: 70:20:10 Fee Tri-Split Distribution Dashboard
-- Description: Tracks allocation into Service Providers (70%), ShieldPool (20%), and Relayer Gas Tank (10%).
-- ==============================================================================
WITH fees AS (
    SELECT 
        block_time,
        bytearray_to_uint256(bytearray_substring(data, 33, 32)) / 1e6 AS total_fee_usdc
    FROM base.logs
    WHERE contract_address = 0x99FEd65Cf2D5378182c3481B300124BB1a8Ad278
      AND topic0 = 0x5a1768417935cf9135fc522bf0da7c688849b251a37c1992797e937d2f349141
)
SELECT 
    date_trunc('day', block_time) AS date,
    SUM(total_fee_usdc) AS total_protocol_revenue_usdc,
    SUM(total_fee_usdc * 0.70) AS providers_and_nodes_70pct_usdc,
    SUM(total_fee_usdc * 0.20) AS agentic_shield_pool_20pct_usdc,
    SUM(total_fee_usdc * 0.10) AS relayer_gas_tank_10pct_usdc
FROM fees
GROUP BY 1
ORDER BY 1 DESC;


-- ==============================================================================
-- QUERY 3: 5 Strategic Sectors & Oracle Domain Breakdown
-- Description: Analyzes economic settlement volume across Trade, Bio, Construction, Compute, M2M.
-- ==============================================================================
WITH deposits AS (
    SELECT 
        block_time,
        bytearray_to_uint256(bytearray_substring(data, 1, 32)) / 1e6 AS deposit_amount_usdc,
        bytearray_to_uint256(bytearray_substring(data, 33, 32)) AS domain_id
    FROM base.logs
    WHERE contract_address = 0x99FEd65Cf2D5378182c3481B300124BB1a8Ad278
      AND topic0 = 0x9a5c88ea56f916de8e2786a45749f96443c683b5ae098d5a6b0c2a26569ec114 -- EscrowDeposited
)
SELECT 
    CASE domain_id
        WHEN 0 THEN '🚢 Global Trade & Logistics'
        WHEN 1 THEN '🧬 Bio & Pharma IP Transfer'
        WHEN 2 THEN '🏗️ Smart Construction (BIM)'
        WHEN 3 THEN '⚡ DePIN GPU & Compute'
        WHEN 4 THEN '💻 M2M Autonomous Outsourcing'
        WHEN 5 THEN '🔋 Energy & Power Grid'
        WHEN 6 THEN '🚚 Autonomous Mobility (E-Seal)'
        ELSE '🌐 Universal Escrow Other'
    END AS industry_sector,
    COUNT(*) AS total_contracts_minted,
    SUM(deposit_amount_usdc) AS total_escrow_capital_usdc,
    ROUND(100.0 * SUM(deposit_amount_usdc) / SUM(SUM(deposit_amount_usdc)) OVER (), 2) AS market_share_percentage
FROM deposits
GROUP BY 1
ORDER BY total_escrow_capital_usdc DESC;


-- ==============================================================================
-- QUERY 4: Adversarial Retaliation & Slashing Leaderboard (Foiled Attacks)
-- Description: Tracks malicious agents slashed for prompt injection, shell tampering, or bad proofs.
-- ==============================================================================
SELECT 
    block_time,
    CONCAT('0x', SUBSTRING(HEX(topic1), 25, 40)) AS attacker_agent_address,
    bytearray_to_uint256(bytearray_substring(data, 1, 32)) AS violation_type,
    bytearray_to_uint256(bytearray_substring(data, 33, 32)) / 1e6 AS confiscated_penalty_usdc,
    tx_hash
FROM base.logs
WHERE contract_address = 0x99FEd65Cf2D5378182c3481B300124BB1a8Ad278
  AND topic0 = 0x8b5b54a72d1746279f0469de22a849f1db89694e9f9bb16ea47d96a75f8f9467 -- AdversarySlashed
ORDER BY block_time DESC
LIMIT 50;


-- ==============================================================================
-- QUERY 5: Cumulative Unique Autonomous Agent Wallets Protected (MAU / WAU)
-- Description: Tracks distinct agent wallets utilizing SafeSecurityGateGuard or Escrow.
-- ==============================================================================
WITH active_agents AS (
    SELECT 
        block_time,
        CONCAT('0x', SUBSTRING(HEX(topic2), 25, 40)) AS agent_address
    FROM base.logs
    WHERE contract_address = 0x99FEd65Cf2D5378182c3481B300124BB1a8Ad278
      AND topic0 = 0x9a5c88ea56f916de8e2786a45749f96443c683b5ae098d5a6b0c2a26569ec114 -- EscrowDeposited
)
SELECT 
    date_trunc('day', block_time) AS date,
    COUNT(DISTINCT agent_address) AS daily_active_agents,
    COUNT(agent_address) AS total_interactions
FROM active_agents
GROUP BY 1
ORDER BY 1 DESC;
