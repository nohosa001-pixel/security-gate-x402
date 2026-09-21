@echo off
title The Sheriff of Agent Finance - AgentEscrow E2E Lifecycle Demo
color 0a
echo ==============================================================================
echo  Agent Security Gate x402 - AgentEscrow Autonomous Slashing Lifecycle Demo
echo ==============================================================================
echo.
echo Launching end-to-end task escrow, collateral staking, and proof-of-safety slashing...
echo Target Contract: 0x8ACafCEce0B1BFE140e75614b90FD1307b6f389d (Polygon Mainnet)
echo Attestation Engine: AgentEscrowEngine (EIP-712 Cryptographic Proofs)
echo.
python scripts\demo_agent_escrow_lifecycle.py
echo.
pause
