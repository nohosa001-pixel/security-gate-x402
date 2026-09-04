"""
Autonomous AI Agent Asset Management & Hedge Fund Risk Engine.
Evaluates agent trading/allocation strategies, audits prompt safety and target protocols,
and issues cryptographic EIP-712 TradeAuthorizations for AgentTreasuryVault.sol.
"""

import time
import secrets
from typing import Dict, Any, Optional, Set
from eth_account.messages import encode_typed_data
from eth_utils import keccak
from app.credit_rating_engine import credit_engine
from app.onchain_signer import onchain_signer
from app.security_engine import audit_payload


class AgentAssetManagementEngine:
    """Evaluates agent fund management strategies and signs EIP-712 TradeAuthorizations."""

    MAX_PERMITTED_SLIPPAGE_BPS = 100  # 1.0% max slippage allowed
    MIN_MANAGER_CREDIT_SCORE = 700     # Grade A or above required for fund management

    def __init__(self):
        self.credit_engine = credit_engine
        self.signer = onchain_signer
        # Default whitelisted protocols (Stage 2 Lending, Stage 4 Factoring, DEX, etc.)
        self.whitelisted_protocols: Set[str] = {
            "0x6418f408cFf03F862D7691f01fAb00a895E6aB93".lower(),  # AgentCreditOracle
            "0x5cC5Afa2a97599d492A3E408Fdd95fD0b520f173".lower(),  # SafeSecurityGateGuard
            "0x9999999999999999999999999999999999999999".lower(),  # AgentFactoringPool mock
            "0x8888888888888888888888888888888888888888".lower(),  # AgentLendingPool mock
            "0x70997970C51812dc3A010C7d01b50e0d17dc79C8".lower(),  # Certified DeFi Strategy Router
        }

    def add_whitelisted_protocol(self, protocol_address: str):
        self.whitelisted_protocols.add(protocol_address.lower())

    def authorize_trade_strategy(
        self,
        strategy_id: int,
        agent_address: str,
        target_protocol: str,
        max_allocation_usdc: float,
        max_slippage_bps: int,
        strategy_rationale: str,
        chain_id: int = 137,
        verifying_contract: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Audits an AI fund manager's proposed trade/rebalance.
        Ensures credit rating qualification, protocol safety, slippage bounds, and prompt integrity.
        """
        if verifying_contract is None:
            verifying_contract = "0x0000000000000000000000000000000000000000"

        # 1. Manager Credit Assessment
        report = self.credit_engine.compute_credit_score(agent_address)
        score = report["credit_score"]
        grade = report["grade"]

        if score < self.MIN_MANAGER_CREDIT_SCORE:
            return {
                "status": "rejected",
                "strategy_id": strategy_id,
                "agent_address": agent_address,
                "is_approved": False,
                "credit_score": score,
                "reason": f"Agent FICO score {score} (Grade {grade}) is below minimum Fund Manager threshold of 700."
            }

        # 2. Strategy Rationale Security Audit (Prompt Injection / Hallucination Check)
        audit = audit_payload(text=strategy_rationale, is_code=False, ground_truth=None)
        if audit.verdict != "PASSED":
            return {
                "status": "rejected",
                "strategy_id": strategy_id,
                "agent_address": agent_address,
                "is_approved": False,
                "risk_score": audit.risk_score,
                "threats": audit.threats,
                "reason": f"Strategy rationale flagged by Security Gate: {audit.threats}"
            }

        # 3. Protocol Whitelist Verification
        if target_protocol.lower() not in self.whitelisted_protocols:
            return {
                "status": "rejected",
                "strategy_id": strategy_id,
                "agent_address": agent_address,
                "target_protocol": target_protocol,
                "is_approved": False,
                "reason": f"Target protocol {target_protocol} is not on the institutional whitelist."
            }

        # 4. Slippage Tolerance Check
        if max_slippage_bps > self.MAX_PERMITTED_SLIPPAGE_BPS:
            return {
                "status": "rejected",
                "strategy_id": strategy_id,
                "is_approved": False,
                "reason": f"Requested slippage {max_slippage_bps} bps exceeds max limit of {self.MAX_PERMITTED_SLIPPAGE_BPS} bps."
            }

        # 5. Cryptographic EIP-712 TradeAuthorization
        strategy_hash = keccak(text=f"STRATEGY:{strategy_id}:{agent_address}:{strategy_rationale}")
        strategy_hash_hex = "0x" + strategy_hash.hex()
        expires_at = int(time.time()) + 900  # Valid for 15 minutes
        nonce = secrets.randbelow(10**9)
        allocation_units = int(max_allocation_usdc * 1_000_000)

        domain_data = {
            "name": "AgentTreasuryVault",
            "version": "1.0.0",
            "chainId": chain_id,
            "verifyingContract": verifying_contract
        }

        types = {
            "EIP712Domain": [
                {"name": "name", "type": "string"},
                {"name": "version", "type": "string"},
                {"name": "chainId", "type": "uint256"},
                {"name": "verifyingContract", "type": "address"}
            ],
            "TradeAuthorization": [
                {"name": "strategyId", "type": "uint256"},
                {"name": "agent", "type": "address"},
                {"name": "targetProtocol", "type": "address"},
                {"name": "maxAllocation", "type": "uint256"},
                {"name": "maxSlippageBps", "type": "uint256"},
                {"name": "strategyHash", "type": "bytes32"},
                {"name": "expiresAt", "type": "uint256"},
                {"name": "nonce", "type": "uint256"}
            ]
        }

        message_data = {
            "strategyId": strategy_id,
            "agent": agent_address,
            "targetProtocol": target_protocol,
            "maxAllocation": allocation_units,
            "maxSlippageBps": max_slippage_bps,
            "strategyHash": strategy_hash,
            "expiresAt": expires_at,
            "nonce": nonce
        }

        structured_data = {
            "types": types,
            "primaryType": "TradeAuthorization",
            "domain": domain_data,
            "message": message_data
        }

        signable_message = encode_typed_data(full_message=structured_data)
        signed = self.signer.account.sign_message(signable_message)

        v = signed.v
        r_hex = "0x" + signed.r.to_bytes(32, "big").hex()
        s_hex = "0x" + signed.s.to_bytes(32, "big").hex()

        return {
            "status": "success",
            "strategy_id": strategy_id,
            "agent_address": agent_address,
            "target_protocol": target_protocol,
            "is_approved": True,
            "credit_score": score,
            "grade": grade,
            "max_allocation_usdc": max_allocation_usdc,
            "max_slippage_bps": max_slippage_bps,
            "strategy_hash": strategy_hash_hex,
            "expires_at": expires_at,
            "attestation": {
                "strategyId": strategy_id,
                "agent": agent_address,
                "targetProtocol": target_protocol,
                "maxAllocation": allocation_units,
                "maxSlippageBps": max_slippage_bps,
                "strategyHash": strategy_hash_hex,
                "expiresAt": expires_at,
                "nonce": nonce,
                "v": v,
                "r": r_hex,
                "s": s_hex,
                "oracle_signer": self.signer.signer_address,
                "chain_id": chain_id
            }
        }

    def calculate_performance_split(self, gross_profit_usdc: float) -> Dict[str, float]:
        """Calculates 15% AI manager fee, 5% Oracle guard fee, and 80% net investor profit."""
        manager_fee = round(gross_profit_usdc * 0.15, 4)
        oracle_fee = round(gross_profit_usdc * 0.05, 4)
        net_investor_profit = round(gross_profit_usdc - manager_fee - oracle_fee, 4)

        return {
            "gross_profit_usdc": gross_profit_usdc,
            "manager_performance_fee_usdc": manager_fee,
            "oracle_guard_fee_usdc": oracle_fee,
            "net_investor_profit_usdc": net_investor_profit,
            "investor_share_pct": 80.0,
            "manager_share_pct": 15.0,
            "oracle_share_pct": 5.0
        }


asset_management_engine = AgentAssetManagementEngine()
