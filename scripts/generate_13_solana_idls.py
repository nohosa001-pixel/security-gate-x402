"""
Generates 13 dedicated standalone Anchor IDL JSON artifacts for all 13 EVM contracts
to enable individual Solscan and SolanaFM verification for the entire suite.
"""

import os
import json

IDL_DIR = os.path.join("contracts", "solana", "idl")
os.makedirs(IDL_DIR, exist_ok=True)

CONTRACT_SPECS = [
    {
        "file": "UniversalEscrowCore.json",
        "name": "universal_escrow_core",
        "program_id": "AGR3W3R9pKxnuZGYrpaggfkbMKVrjoniLaGvi1voBFSC",
        "description": "Universal Modular Escrow Core: Zero-Deficit Split Settlement & Ed25519 Attestations",
        "instructions": [
            {
                "name": "initializeJob",
                "docs": ["Initializes an escrow job with domain verification requirement"],
                "accounts": [
                    {"name": "jobAccount", "isMut": True, "isSigner": False},
                    {"name": "payer", "isMut": True, "isSigner": True},
                    {"name": "systemProgram", "isMut": False, "isSigner": False}
                ],
                "args": [
                    {"name": "jobId", "type": {"array": ["u8", 32]}},
                    {"name": "domain", "type": "u8"},
                    {"name": "truthHashRequirement", "type": {"array": ["u8", 32]}},
                    {"name": "totalDeposit", "type": "u64"},
                    {"name": "deadline", "type": "i64"}
                ]
            },
            {
                "name": "settleJob",
                "docs": ["Settles job and disburses SPL USDC according to recipients hash"],
                "accounts": [
                    {"name": "jobAccount", "isMut": True, "isSigner": False},
                    {"name": "payer", "isMut": True, "isSigner": False},
                    {"name": "treasury", "isMut": True, "isSigner": False},
                    {"name": "systemProgram", "isMut": False, "isSigner": False}
                ],
                "args": [
                    {"name": "jobId", "type": {"array": ["u8", 32]}},
                    {"name": "domain", "type": "u8"},
                    {"name": "truthHash", "type": {"array": ["u8", 32]}},
                    {"name": "recipientsHash", "type": {"array": ["u8", 32]}},
                    {"name": "expiresAt", "type": "i64"},
                    {"name": "signature", "type": {"array": ["u8", 64]}}
                ]
            }
        ],
        "accounts": [
            {
                "name": "EscrowJobAccount",
                "type": {
                    "kind": "struct",
                    "fields": [
                        {"name": "jobId", "type": {"array": ["u8", 32]}},
                        {"name": "payer", "type": "pubkey"},
                        {"name": "domain", "type": "u8"},
                        {"name": "truthHashRequirement", "type": {"array": ["u8", 32]}},
                        {"name": "totalDeposit", "type": "u64"},
                        {"name": "deadline", "type": "i64"},
                        {"name": "isSettled", "type": "bool"}
                    ]
                }
            }
        ]
    },
    {
        "file": "AgentComplianceRegistry.json",
        "name": "agent_compliance_registry",
        "program_id": "AGRGksgAaU1D2cESdYGbFoV4zty3t8D7LacfZ6qcejKe",
        "description": "Agent Compliance Registry: EU AI Act & ISO-42001 proof registration",
        "instructions": [
            {
                "name": "registerCompliance",
                "docs": ["Registers EU AI Act / ISO-42001 proof of compliance"],
                "accounts": [
                    {"name": "complianceRecord", "isMut": True, "isSigner": False},
                    {"name": "authority", "isMut": True, "isSigner": True},
                    {"name": "systemProgram", "isMut": False, "isSigner": False}
                ],
                "args": [
                    {"name": "agentId", "type": "pubkey"},
                    {"name": "complianceHash", "type": {"array": ["u8", 32]}},
                    {"name": "jurisdiction", "type": "string"},
                    {"name": "riskTier", "type": "u8"}
                ]
            }
        ],
        "accounts": [
            {
                "name": "ComplianceRecordAccount",
                "type": {
                    "kind": "struct",
                    "fields": [
                        {"name": "agentId", "type": "pubkey"},
                        {"name": "complianceHash", "type": {"array": ["u8", 32]}},
                        {"name": "jurisdiction", "type": "string"},
                        {"name": "riskTier", "type": "u8"},
                        {"name": "registeredAt", "type": "i64"}
                    ]
                }
            }
        ]
    },
    {
        "file": "AgentCreditOracle.json",
        "name": "agent_credit_oracle",
        "program_id": "AGRrNBZUAG2CxcxxQW7SGtWY3EMT3JAcVyqwV8ft5GxL",
        "description": "Agent Credit Oracle: Deterministic AI credit rating & audit records",
        "instructions": [
            {
                "name": "updateAgentCredit",
                "docs": ["Records deterministic credit rating & audit history"],
                "accounts": [
                    {"name": "creditAccount", "isMut": True, "isSigner": False},
                    {"name": "authority", "isMut": True, "isSigner": True},
                    {"name": "systemProgram", "isMut": False, "isSigner": False}
                ],
                "args": [
                    {"name": "agentId", "type": "pubkey"},
                    {"name": "creditScore", "type": "u16"},
                    {"name": "riskScore", "type": "u8"},
                    {"name": "completedAudits", "type": "u32"}
                ]
            }
        ],
        "accounts": [
            {
                "name": "AgentCreditAccount",
                "type": {
                    "kind": "struct",
                    "fields": [
                        {"name": "agentId", "type": "pubkey"},
                        {"name": "creditScore", "type": "u16"},
                        {"name": "riskScore", "type": "u8"},
                        {"name": "completedAudits", "type": "u32"},
                        {"name": "lastUpdated", "type": "i64"}
                    ]
                }
            }
        ]
    },
    {
        "file": "AgentEscrow.json",
        "name": "agent_escrow",
        "program_id": "AGRpSZ24g4aWuQsB6zf7F8KvYuySZHnyAwu155mMp26q",
        "description": "Agent Escrow: Traditional M2M autonomous escrow & split settlement",
        "instructions": [
            {
                "name": "createM2mEscrow",
                "docs": ["Traditional M2M autonomous escrow & split settlement"],
                "accounts": [
                    {"name": "escrowAccount", "isMut": True, "isSigner": False},
                    {"name": "payer", "isMut": True, "isSigner": True},
                    {"name": "payerTokenAccount", "isMut": True, "isSigner": False},
                    {"name": "escrowTokenAccount", "isMut": True, "isSigner": False},
                    {"name": "tokenProgram", "isMut": False, "isSigner": False},
                    {"name": "systemProgram", "isMut": False, "isSigner": False}
                ],
                "args": [
                    {"name": "jobId", "type": {"array": ["u8", 32]}},
                    {"name": "amount", "type": "u64"},
                    {"name": "payee", "type": "pubkey"}
                ]
            }
        ],
        "accounts": [
            {
                "name": "M2MEscrowAccount",
                "type": {
                    "kind": "struct",
                    "fields": [
                        {"name": "jobId", "type": {"array": ["u8", 32]}},
                        {"name": "payer", "type": "pubkey"},
                        {"name": "payee", "type": "pubkey"},
                        {"name": "amount", "type": "u64"},
                        {"name": "status", "type": "u8"}
                    ]
                }
            }
        ]
    },
    {
        "file": "AgentFactoringPool.json",
        "name": "agent_factoring_pool",
        "program_id": "AGRKvCc7edgq1T2KzLwMzUp3S8M8Muy5hv9H7MrZjtEZ",
        "description": "Agent Factoring Pool: Invoice factoring & accounts-receivable advances",
        "instructions": [
            {
                "name": "requestFactoringAdvance",
                "docs": ["Invoice & accounts-receivable factoring advances"],
                "accounts": [
                    {"name": "factoringAccount", "isMut": True, "isSigner": False},
                    {"name": "borrower", "isMut": True, "isSigner": True},
                    {"name": "systemProgram", "isMut": False, "isSigner": False}
                ],
                "args": [
                    {"name": "invoiceHash", "type": {"array": ["u8", 32]}},
                    {"name": "advanceAmount", "type": "u64"},
                    {"name": "discountFee", "type": "u64"}
                ]
            }
        ],
        "accounts": [
            {
                "name": "FactoringAccount",
                "type": {
                    "kind": "struct",
                    "fields": [
                        {"name": "invoiceHash", "type": {"array": ["u8", 32]}},
                        {"name": "borrower", "type": "pubkey"},
                        {"name": "advanceAmount", "type": "u64"},
                        {"name": "discountFee", "type": "u64"},
                        {"name": "isRepaid", "type": "bool"}
                    ]
                }
            }
        ]
    },
    {
        "file": "AgentInsurancePool.json",
        "name": "agent_insurance_pool",
        "program_id": "AGRE6ojRp1pbnYT8QEJ34reGstETHeYGdLncoBc34hQh",
        "description": "Agent Insurance Pool: Autonomous risk underwriting & slashing protection",
        "instructions": [
            {
                "name": "fileInsuranceClaim",
                "docs": ["Underwriting & slashing indemnification claims"],
                "accounts": [
                    {"name": "claimRecord", "isMut": True, "isSigner": False},
                    {"name": "claimant", "isMut": True, "isSigner": True},
                    {"name": "systemProgram", "isMut": False, "isSigner": False}
                ],
                "args": [
                    {"name": "incidentHash", "type": {"array": ["u8", 32]}},
                    {"name": "claimedPayout", "type": "u64"}
                ]
            }
        ],
        "accounts": [
            {
                "name": "InsuranceClaimAccount",
                "type": {
                    "kind": "struct",
                    "fields": [
                        {"name": "incidentHash", "type": {"array": ["u8", 32]}},
                        {"name": "claimant", "type": "pubkey"},
                        {"name": "claimedPayout", "type": "u64"},
                        {"name": "approved", "type": "bool"}
                    ]
                }
            }
        ]
    },
    {
        "file": "AgentLendingPool.json",
        "name": "agent_lending_pool",
        "program_id": "AGRuKsgaKpqacjcPvKehAFyfxVQhD3mBUsjfTqL7yGaT",
        "description": "Agent Lending Pool: Flash loans & credit-line undercollateralized loans",
        "instructions": [
            {
                "name": "borrowCreditLoan",
                "docs": ["Flash loans & credit-line undercollateralized loans"],
                "accounts": [
                    {"name": "loanAccount", "isMut": True, "isSigner": False},
                    {"name": "borrower", "isMut": True, "isSigner": True},
                    {"name": "systemProgram", "isMut": False, "isSigner": False}
                ],
                "args": [
                    {"name": "loanAmount", "type": "u64"},
                    {"name": "interestBps", "type": "u16"}
                ]
            }
        ],
        "accounts": [
            {
                "name": "CreditLoanAccount",
                "type": {
                    "kind": "struct",
                    "fields": [
                        {"name": "borrower", "type": "pubkey"},
                        {"name": "loanAmount", "type": "u64"},
                        {"name": "interestBps", "type": "u16"},
                        {"name": "dueDate", "type": "i64"}
                    ]
                }
            }
        ]
    },
    {
        "file": "AgentTreasuryVault.json",
        "name": "agent_treasury_vault",
        "program_id": "AGRUfTxpEKMbG9yxasuoGxGFPp2y3PYEBwEpDUSqpfXQ",
        "description": "Agent Treasury Vault: Sovereign 100% T-Bill RWA collateral vault",
        "instructions": [
            {
                "name": "depositTreasuryToll",
                "docs": ["Sovereign 100% T-Bill RWA collateral vault toll deposits"],
                "accounts": [
                    {"name": "treasuryAccount", "isMut": True, "isSigner": False},
                    {"name": "depositor", "isMut": True, "isSigner": True},
                    {"name": "systemProgram", "isMut": False, "isSigner": False}
                ],
                "args": [
                    {"name": "amount", "type": "u64"},
                    {"name": "destinationTreasury", "type": "pubkey"}
                ]
            }
        ],
        "accounts": [
            {
                "name": "TreasuryVaultAccount",
                "type": {
                    "kind": "struct",
                    "fields": [
                        {"name": "totalTollCollected", "type": "u128"},
                        {"name": "vaultAuthority", "type": "pubkey"},
                        {"name": "lastDepositAt", "type": "i64"}
                    ]
                }
            }
        ]
    },
    {
        "file": "GuardableBySecurityGate.json",
        "name": "guardable_by_security_gate",
        "program_id": "AGR2YR7c5JyL6zmEpZA6rduVTTFSftPKXToeTFj6wQRB",
        "description": "Guardable By Security Gate: Modifiers & gating enforcement hooks",
        "instructions": [
            {
                "name": "guardAccountAccess",
                "docs": ["Modifiers & gating enforcement hooks"],
                "accounts": [
                    {"name": "guardAccount", "isMut": True, "isSigner": False},
                    {"name": "targetContract", "isMut": False, "isSigner": False},
                    {"name": "signer", "isMut": True, "isSigner": True}
                ],
                "args": [
                    {"name": "proofHash", "type": {"array": ["u8", 32]}}
                ]
            }
        ],
        "accounts": [
            {
                "name": "GuardAccess",
                "type": {
                    "kind": "struct",
                    "fields": [
                        {"name": "isEnforced", "type": "bool"},
                        {"name": "targetContract", "type": "pubkey"}
                    ]
                }
            }
        ]
    },
    {
        "file": "ITruthAdapter.json",
        "name": "i_truth_adapter",
        "program_id": "AGReYJAsoJJA7N4wE8oZNgqzhcu6LNnSyBRUMhG8mP7A",
        "description": "ITruthAdapter Standard Interface: Common traits and domain types",
        "instructions": [
            {
                "name": "verifyTruthInterface",
                "docs": ["Standard domain truth verification interface check"],
                "accounts": [
                    {"name": "truthAccount", "isMut": False, "isSigner": False}
                ],
                "args": [
                    {"name": "domain", "type": "u8"},
                    {"name": "truthHash", "type": {"array": ["u8", 32]}}
                ]
            }
        ],
        "accounts": [
            {
                "name": "TruthInterfaceAccount",
                "type": {
                    "kind": "struct",
                    "fields": [
                        {"name": "domain", "type": "u8"},
                        {"name": "isRegistered", "type": "bool"}
                    ]
                }
            }
        ]
    },
    {
        "file": "TruthAdapter.json",
        "name": "truth_adapter",
        "program_id": "AGRCVvz3oYrsPC5vfuWHFPNy9nSqZF54BUXDvRVRhbT",
        "description": "Truth Adapter: Domain-specific truth & AI attestation verification adapter",
        "instructions": [
            {
                "name": "verifyDomainTruth",
                "docs": ["Modular multi-domain truth verification & adapter binding"],
                "accounts": [
                    {"name": "truthAccount", "isMut": True, "isSigner": False},
                    {"name": "oracleSigner", "isMut": True, "isSigner": True}
                ],
                "args": [
                    {"name": "domain", "type": "u8"},
                    {"name": "jobId", "type": {"array": ["u8", 32]}},
                    {"name": "truthHash", "type": {"array": ["u8", 32]}}
                ]
            }
        ],
        "accounts": [
            {
                "name": "VerifyDomainTruth",
                "type": {
                    "kind": "struct",
                    "fields": [
                        {"name": "domain", "type": "u8"},
                        {"name": "jobId", "type": {"array": ["u8", 32]}},
                        {"name": "truthHash", "type": {"array": ["u8", 32]}},
                        {"name": "verified", "type": "bool"}
                    ]
                }
            }
        ]
    },
    {
        "file": "SafeSecurityGateGuard.json",
        "name": "safe_security_gate_guard",
        "program_id": "AGRAtNxF474xZFin5iZaxBKE2fKNKPih7qYPEm3mu9oN",
        "description": "Safe Security Gate Guard: Safe Multisig execution guard enforcement",
        "instructions": [
            {
                "name": "verifyMultisigGuard",
                "docs": ["Safe Multisig execution guard & pre/post verification"],
                "accounts": [
                    {"name": "safeGuardAccount", "isMut": True, "isSigner": False},
                    {"name": "multisig", "isMut": False, "isSigner": True}
                ],
                "args": [
                    {"name": "txHash", "type": {"array": ["u8", 32]}}
                ]
            }
        ],
        "accounts": [
            {
                "name": "VerifyMultisigGuard",
                "type": {
                    "kind": "struct",
                    "fields": [
                        {"name": "multisig", "type": "pubkey"},
                        {"name": "txHash", "type": {"array": ["u8", 32]}},
                        {"name": "approved", "type": "bool"}
                    ]
                }
            }
        ]
    },
    {
        "file": "SecurityGateConsumer.json",
        "name": "security_gate_consumer",
        "program_id": "AGRivmSTXUQFBgnn3zUDt76qjDJW9Q3W6UVXVPsj6siH",
        "description": "Security Gate Consumer: Consumer contract mixin & protocol client",
        "instructions": [
            {
                "name": "verifyConsumerGate",
                "docs": ["Consumer contract mixin & security protocol verification"],
                "accounts": [
                    {"name": "consumerRecord", "isMut": True, "isSigner": False},
                    {"name": "consumer", "isMut": True, "isSigner": True}
                ],
                "args": [
                    {"name": "agentId", "type": "pubkey"},
                    {"name": "proofHash", "type": {"array": ["u8", 32]}}
                ]
            }
        ],
        "accounts": [
            {
                "name": "VerifyConsumerGate",
                "type": {
                    "kind": "struct",
                    "fields": [
                        {"name": "consumer", "type": "publicKey"},
                        {"name": "agentId", "type": "publicKey"},
                        {"name": "verified", "type": "bool"}
                    ]
                }
            }
        ]
    }
]

def main():
    print(f"Generating 13 dedicated Anchor IDLs in {IDL_DIR}...")
    for spec in CONTRACT_SPECS:
        idl_content = {
            "version": "0.1.0",
            "name": spec["name"],
            "metadata": {
                "address": spec["program_id"],
                "origin": "anchor",
                "description": spec["description"]
            },
            "instructions": spec["instructions"],
            "accounts": spec["accounts"],
            "types": [],
            "events": [],
            "errors": [
                {"code": 6000, "name": "InvalidSignature", "msg": "Cryptographic Ed25519 signature invalid"},
                {"code": 6001, "name": "UnauthorizedCaller", "msg": "Caller lacks required authority"}
            ]
        }
        target_path = os.path.join(IDL_DIR, spec["file"])
        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(idl_content, f, indent=2)
        print(f"  [OK] {spec['file']} -> {spec['program_id']}")
    print("Done! Exactly 13 dedicated IDL files generated.")

if __name__ == "__main__":
    main()
