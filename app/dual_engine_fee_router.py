"""Dual-Engine Dynamic Fee Router for security-gate-x402.

Implements the 2-Tier Hybrid Monetization Engine:
- Tier 1: Micro-Toll ($0.002 USDC flat) for high-throughput AST/DLP/tool calls
- Tier 2: Clearinghouse Take-Rate (0.3% - 1.0% of GMV) for conditional escrow settlements

Provides cryptographic rebate mechanisms for verified Proof-of-Safety agents:
- Verified Agent: 20-33% fee discount + instant escrow finality (0s challenge window)
- Unverified Agent: +50% risk surcharge + 24-hour escrow challenge delay

Enforces protocol revenue split:
- 70% Protocol Treasury Vault
- 20% Agentic Shield Pool (on-chain malpractice insurance)
- 10% Relayer Gas Tank (L2 meta-tx subsidization)
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Optional, Tuple


class FeeTier(str, Enum):
    TIER_1_MICRO_TOLL = "Tier-1-Micro-Toll"
    TIER_2_CLEARING_TAKE_RATE = "Tier-2-Clearing-Take-Rate"


class DualEngineFeeRouter:
    """Calculates dynamic routing fees, discounts, and protocol revenue splits."""

    # Tier 1 Parameters
    TIER1_FLAT_USDC_UNITS = 2000  # $0.002 USDC (6 decimals)
    
    # Tier 2 Parameters
    DEFAULT_TAKE_RATE_BPS = 50    # 0.50% base clearing fee
    MIN_TAKE_RATE_BPS = 30        # 0.30% floor
    MAX_TAKE_RATE_BPS = 100       # 1.00% cap
    BPS_DENOMINATOR = 10000

    # Cryptographic Rebate & Penalty
    VERIFIED_DISCOUNT_PERCENT = 20  # 20% discount with EIP-712 Proof-of-Safety
    UNVERIFIED_SURCHARGE_PERCENT = 50  # +50% risk surcharge without proof

    # Revenue Split (70 / 20 / 10)
    TREASURY_SHARE_PERCENT = 70
    SHIELD_POOL_SHARE_PERCENT = 20
    GAS_TANK_SHARE_PERCENT = 10

    # Official Gateway Attestation Endpoint
    OFFICIAL_GATEWAY_URL = "https://agent-security-gate-x402-212942243360.asia-northeast3.run.app/api/v1/escrow/audit"

    @classmethod
    def classify_tier(cls, is_escrow_settlement: bool = False, gmv_usdc_units: int = 0) -> FeeTier:
        """Determines whether transaction is Tier 1 (Micro-Toll) or Tier 2 (Clearing)."""
        if is_escrow_settlement or gmv_usdc_units > 10_000_000:  # > $10.00 GMV or escrow
            return FeeTier.TIER_2_CLEARING_TAKE_RATE
        return FeeTier.TIER_1_MICRO_TOLL

    @classmethod
    def calculate_settlement_fee(
        cls,
        is_escrow: bool,
        gmv_usdc_units: int,
        has_proof_of_safety: bool,
        risk_score: int = 0  # 0 to 100
    ) -> Dict[str, Any]:
        """Calculates exact fee, discount, finality mode, and splits."""
        tier = cls.classify_tier(is_escrow, gmv_usdc_units)

        if tier == FeeTier.TIER_1_MICRO_TOLL:
            base_fee = cls.TIER1_FLAT_USDC_UNITS
            if has_proof_of_safety:
                # 20% discount on micro-toll ($0.0016)
                final_fee = int(base_fee * (100 - cls.VERIFIED_DISCOUNT_PERCENT) / 100)
            else:
                # +50% unverified surcharge ($0.0030)
                final_fee = int(base_fee * (100 + cls.UNVERIFIED_SURCHARGE_PERCENT) / 100)
            
            take_rate_bps = 0
            instant_finality = True
            challenge_period_sec = 0
        else:
            # Tier 2: Dynamic Take Rate scaled by risk score
            # Base 50 bps, adjusted + (risk_score * 0.3)
            adjusted_bps = cls.DEFAULT_TAKE_RATE_BPS + int((risk_score / 100) * 30)
            adjusted_bps = max(cls.MIN_TAKE_RATE_BPS, min(cls.MAX_TAKE_RATE_BPS, adjusted_bps))

            if has_proof_of_safety:
                # Discount bps by 20%
                take_rate_bps = int(adjusted_bps * (100 - cls.VERIFIED_DISCOUNT_PERCENT) / 100)
                instant_finality = True
                challenge_period_sec = 0
            else:
                # Add 50% risk surcharge
                take_rate_bps = int(adjusted_bps * (100 + cls.UNVERIFIED_SURCHARGE_PERCENT) / 100)
                instant_finality = False
                challenge_period_sec = 86400  # 24-hour mandatory delay

            final_fee = (gmv_usdc_units * take_rate_bps) // cls.BPS_DENOMINATOR

        # Revenue Split
        splits = cls.split_protocol_revenue(final_fee)

        return {
            "tier": tier.value,
            "gmv_usdc_units": gmv_usdc_units,
            "has_proof_of_safety": has_proof_of_safety,
            "final_fee_units": final_fee,
            "final_fee_usd": round(final_fee / 1_000_000, 6),
            "take_rate_bps": take_rate_bps,
            "instant_finality": instant_finality,
            "challenge_period_seconds": challenge_period_sec,
            "splits": splits,
        }

    @classmethod
    def split_protocol_revenue(cls, total_fee_units: int) -> Dict[str, int]:
        """Splits collected protocol revenue 70% Treasury / 20% Shield / 10% Gas."""
        treasury_amt = (total_fee_units * cls.TREASURY_SHARE_PERCENT) // 100
        shield_amt = (total_fee_units * cls.SHIELD_POOL_SHARE_PERCENT) // 100
        gas_amt = total_fee_units - (treasury_amt + shield_amt)  # remaining 10%
        return {
            "treasury_vault": treasury_amt,
            "agentic_shield_pool": shield_amt,
            "relayer_gas_tank": gas_amt,
        }

    @classmethod
    def build_x402_headers(
        cls,
        standard_price_units: int = 15000,   # $0.015 USDC
        guarded_price_units: int = 10000,    # $0.010 USDC (with Proof-of-Safety)
        tier: FeeTier = FeeTier.TIER_1_MICRO_TOLL,
    ) -> Dict[str, str]:
        """Constructs standardized HTTP 402 pricing and incentive headers for external agents."""
        return {
            "X-402-Price-Standard": str(standard_price_units),
            "X-402-Price-Guarded": str(guarded_price_units),
            "X-402-Gate-Endpoint": cls.OFFICIAL_GATEWAY_URL,
            "X-402-Proof-Rebate-Bps": "2000",  # 20% discount
            "X-402-Settlement-Tier": tier.value,
            "X-402-Instant-Finality": "Available-With-Proof",
        }
