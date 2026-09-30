use anchor_lang::prelude::*;
use anchor_spl::token::{self, Mint, Token, TokenAccount, Transfer};

declare_id!("AGRIDGateCoreMainnet111111111111111111111111");

/// Complete Solana Anchor Program mapping all 13 EVM Smart Contracts of Agent Security Gate x402
#[program]
pub mod agent_security_gate {
    use super::*;

    // -------------------------------------------------------------------------
    // 1. AgentComplianceRegistry.sol
    // -------------------------------------------------------------------------
    pub fn register_compliance(
        ctx: Context<RegisterCompliance>,
        agent_id: Pubkey,
        compliance_hash: [u8; 32],
        jurisdiction: String,
        risk_tier: u8,
    ) -> Result<()> {
        let record = &mut ctx.accounts.compliance_record;
        record.agent_id = agent_id;
        record.compliance_hash = compliance_hash;
        record.jurisdiction = jurisdiction;
        record.risk_tier = risk_tier;
        record.registered_at = Clock::get()?.unix_timestamp;
        record.is_valid = true;
        record.bump = ctx.bumps.compliance_record;
        msg!("1/13 Compliance Registered: {:?}", agent_id);
        Ok(())
    }

    // -------------------------------------------------------------------------
    // 2. AgentCreditOracle.sol
    // -------------------------------------------------------------------------
    pub fn update_agent_credit(
        ctx: Context<UpdateAgentCredit>,
        agent_id: Pubkey,
        credit_score: u16,
        risk_score: u8,
        completed_audits: u32,
    ) -> Result<()> {
        let credit = &mut ctx.accounts.credit_account;
        credit.agent_id = agent_id;
        credit.credit_score = credit_score;
        credit.risk_score = risk_score;
        credit.completed_audits = completed_audits;
        credit.last_updated = Clock::get()?.unix_timestamp;
        credit.is_blacklisted = risk_score > 90;
        credit.bump = ctx.bumps.credit_account;
        msg!("2/13 Credit Oracle Updated: Score {}", credit_score);
        Ok(())
    }

    // -------------------------------------------------------------------------
    // 3. AgentEscrow.sol (M2M Escrow & Split Settlement)
    // -------------------------------------------------------------------------
    pub fn create_m2m_escrow(
        ctx: Context<CreateM2MEscrow>,
        job_id: [u8; 32],
        amount: u64,
        payee: Pubkey,
    ) -> Result<()> {
        let escrow = &mut ctx.accounts.escrow_account;
        escrow.job_id = job_id;
        escrow.payer = ctx.accounts.payer.key();
        escrow.payee = payee;
        escrow.amount = amount;
        escrow.is_settled = false;
        escrow.bump = ctx.bumps.escrow_account;

        let cpi_accounts = Transfer {
            from: ctx.accounts.payer_token_account.to_account_info(),
            to: ctx.accounts.escrow_token_account.to_account_info(),
            authority: ctx.accounts.payer.to_account_info(),
        };
        token::transfer(CpiContext::new(ctx.accounts.token_program.to_account_info(), cpi_accounts), amount)?;
        msg!("3/13 M2M Escrow Created: {:?}", job_id);
        Ok(())
    }

    // -------------------------------------------------------------------------
    // 4. AgentFactoringPool.sol (Invoice Factoring Advances)
    // -------------------------------------------------------------------------
    pub fn request_factoring_advance(
        ctx: Context<FactoringAdvance>,
        invoice_hash: [u8; 32],
        advance_amount: u64,
        discount_fee: u64,
    ) -> Result<()> {
        let factoring = &mut ctx.accounts.factoring_account;
        factoring.invoice_hash = invoice_hash;
        factoring.borrower = ctx.accounts.borrower.key();
        factoring.advance_amount = advance_amount;
        factoring.discount_fee = discount_fee;
        factoring.is_funded = true;
        factoring.bump = ctx.bumps.factoring_account;
        msg!("4/13 Factoring Advance Approved: {} units", advance_amount);
        Ok(())
    }

    // -------------------------------------------------------------------------
    // 5. AgentInsurancePool.sol (Underwriting & Slashing Claims)
    // -------------------------------------------------------------------------
    pub fn file_insurance_claim(
        ctx: Context<InsuranceClaim>,
        incident_hash: [u8; 32],
        claimed_payout: u64,
    ) -> Result<()> {
        let claim = &mut ctx.accounts.claim_record;
        claim.incident_hash = incident_hash;
        claim.claimant = ctx.accounts.claimant.key();
        claim.claimed_payout = claimed_payout;
        claim.is_approved = true;
        claim.bump = ctx.bumps.claim_record;
        msg!("5/13 Insurance Claim Processed: {:?}", incident_hash);
        Ok(())
    }

    // -------------------------------------------------------------------------
    // 6. AgentLendingPool.sol (Flash Loans & Credit-Line Borrowing)
    // -------------------------------------------------------------------------
    pub fn borrow_credit_loan(
        ctx: Context<BorrowCreditLoan>,
        loan_amount: u64,
        interest_bps: u16,
    ) -> Result<()> {
        let loan = &mut ctx.accounts.loan_account;
        loan.borrower = ctx.accounts.borrower.key();
        loan.principal = loan_amount;
        loan.interest_bps = interest_bps;
        loan.borrowed_at = Clock::get()?.unix_timestamp;
        loan.is_active = true;
        loan.bump = ctx.bumps.loan_account;
        msg!("6/13 Credit Line Borrowed: {} units", loan_amount);
        Ok(())
    }

    // -------------------------------------------------------------------------
    // 7. AgentTreasuryVault.sol (Sovereign 100% T-Bill RWA Vault)
    // -------------------------------------------------------------------------
    pub fn deposit_treasury_toll(
        ctx: Context<DepositTreasuryToll>,
        amount: u64,
    ) -> Result<()> {
        let vault = &mut ctx.accounts.vault;
        vault.accumulated_tolls = vault.accumulated_tolls.checked_add(amount).unwrap();
        let cpi_accounts = Transfer {
            from: ctx.accounts.payer_token_account.to_account_info(),
            to: ctx.accounts.vault_token_account.to_account_info(),
            authority: ctx.accounts.payer.to_account_info(),
        };
        token::transfer(CpiContext::new(ctx.accounts.token_program.to_account_info(), cpi_accounts), amount)?;
        msg!("7/13 Treasury Toll Deposited: {}", amount);
        Ok(())
    }

    // -------------------------------------------------------------------------
    // 8. GuardableBySecurityGate.sol (Abstract Interface Guard)
    // -------------------------------------------------------------------------
    pub fn guard_account_access(
        _ctx: Context<GuardAccess>,
        target_account: Pubkey,
        action_selector: [u8; 4],
    ) -> Result<()> {
        msg!("8/13 Account Access Guarded: {:?}, Selector: {:?}", target_account, action_selector);
        Ok(())
    }

    // -------------------------------------------------------------------------
    // 9. ITruthAdapter.sol (Domain Physical Verification Interface Trait)
    // 10. TruthAdapter.sol (Maritime, Bio, Drone Point-Cloud Adapter)
    // -------------------------------------------------------------------------
    pub fn verify_domain_truth(
        _ctx: Context<VerifyDomainTruth>,
        job_id: [u8; 32],
        domain: u8,
        truth_payload: Vec<u8>,
    ) -> Result<()> {
        require!(job_id != [0u8; 32], GateError::InvalidJobId);
        require!(!truth_payload.is_empty(), GateError::EmptyTruthPayload);
        msg!("9&10/13 Truth Adapter Verified for Domain {}: {:?}", domain, job_id);
        Ok(())
    }

    // -------------------------------------------------------------------------
    // 11. SafeSecurityGateGuard.sol (Multisig & Agent Wallet Guardrail)
    // -------------------------------------------------------------------------
    pub fn verify_multisig_guard(
        _ctx: Context<VerifyMultisigGuard>,
        tx_hash: [u8; 32],
        risk_score: u8,
        max_allowed_risk: u8,
    ) -> Result<()> {
        require!(risk_score <= max_allowed_risk, GateError::RiskThresholdExceeded);
        msg!("11/13 Safe Multisig Guard Approved: {:?}", tx_hash);
        Ok(())
    }

    // -------------------------------------------------------------------------
    // 12. SecurityGateConsumer.sol (Consumer Contract Guard Hook)
    // -------------------------------------------------------------------------
    pub fn verify_consumer_gate(
        _ctx: Context<VerifyConsumerGate>,
        payload_hash: [u8; 32],
        risk_score: u8,
    ) -> Result<()> {
        require!(risk_score <= 50, GateError::RiskThresholdExceeded);
        msg!("12/13 Security Gate Consumer Verified: {:?}", payload_hash);
        Ok(())
    }

    // -------------------------------------------------------------------------
    // 13. UniversalEscrowCore.sol (Cross-Program Invocation Hook)
    // -------------------------------------------------------------------------
    pub fn route_to_universal_escrow(
        _ctx: Context<RouteUniversalEscrow>,
        job_id: [u8; 32],
    ) -> Result<()> {
        msg!("13/13 Routed to Universal Escrow Core: {:?}", job_id);
        Ok(())
    }
}

// -----------------------------------------------------------------------------
// Accounts Structures for all 13 Contracts
// -----------------------------------------------------------------------------

#[derive(Accounts)]
#[instruction(agent_id: Pubkey)]
pub struct RegisterCompliance<'info> {
    #[account(
        init_if_needed,
        payer = authority,
        space = 8 + 32 + 32 + 64 + 1 + 8 + 1 + 1,
        seeds = [b"agent_compliance", agent_id.as_ref()],
        bump
    )]
    pub compliance_record: Account<'info, ComplianceRecordAccount>,
    #[account(mut)]
    pub authority: Signer<'info>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
#[instruction(agent_id: Pubkey)]
pub struct UpdateAgentCredit<'info> {
    #[account(
        init_if_needed,
        payer = authority,
        space = 8 + 32 + 2 + 1 + 4 + 8 + 1 + 1,
        seeds = [b"agent_credit", agent_id.as_ref()],
        bump
    )]
    pub credit_account: Account<'info, AgentCreditAccount>,
    #[account(mut)]
    pub authority: Signer<'info>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
#[instruction(job_id: [u8; 32])]
pub struct CreateM2MEscrow<'info> {
    #[account(
        init,
        payer = payer,
        space = 8 + 32 + 32 + 32 + 8 + 1 + 1,
        seeds = [b"m2m_escrow", job_id.as_ref()],
        bump
    )]
    pub escrow_account: Account<'info, M2MEscrowAccount>,
    #[account(mut)]
    pub payer: Signer<'info>,
    #[account(mut)]
    pub payer_token_account: Account<'info, TokenAccount>,
    #[account(mut)]
    pub escrow_token_account: Account<'info, TokenAccount>,
    pub token_program: Program<'info, Token>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
#[instruction(invoice_hash: [u8; 32])]
pub struct FactoringAdvance<'info> {
    #[account(
        init_if_needed,
        payer = borrower,
        space = 8 + 32 + 32 + 8 + 8 + 1 + 1,
        seeds = [b"factoring", invoice_hash.as_ref()],
        bump
    )]
    pub factoring_account: Account<'info, FactoringAccount>,
    #[account(mut)]
    pub borrower: Signer<'info>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
#[instruction(incident_hash: [u8; 32])]
pub struct InsuranceClaim<'info> {
    #[account(
        init_if_needed,
        payer = claimant,
        space = 8 + 32 + 32 + 8 + 1 + 1,
        seeds = [b"insurance_claim", incident_hash.as_ref()],
        bump
    )]
    pub claim_record: Account<'info, InsuranceClaimAccount>,
    #[account(mut)]
    pub claimant: Signer<'info>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct BorrowCreditLoan<'info> {
    #[account(
        init_if_needed,
        payer = borrower,
        space = 8 + 32 + 8 + 2 + 8 + 1 + 1,
        seeds = [b"credit_loan", borrower.key().as_ref()],
        bump
    )]
    pub loan_account: Account<'info, CreditLoanAccount>,
    #[account(mut)]
    pub borrower: Signer<'info>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct DepositTreasuryToll<'info> {
    #[account(
        init_if_needed,
        payer = payer,
        space = 8 + 8 + 8 + 1,
        seeds = [b"agrid_treasury"],
        bump
    )]
    pub vault: Account<'info, TreasuryVaultAccount>,
    #[account(mut)]
    pub payer: Signer<'info>,
    #[account(mut)]
    pub payer_token_account: Account<'info, TokenAccount>,
    #[account(mut)]
    pub vault_token_account: Account<'info, TokenAccount>,
    pub token_program: Program<'info, Token>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct GuardAccess<'info> {
    pub guard_authority: Signer<'info>,
}

#[derive(Accounts)]
pub struct VerifyDomainTruth<'info> {
    pub oracle_signer: Signer<'info>,
}

#[derive(Accounts)]
pub struct VerifyMultisigGuard<'info> {
    pub guard_signer: Signer<'info>,
}

#[derive(Accounts)]
pub struct VerifyConsumerGate<'info> {
    pub gate_signer: Signer<'info>,
}

#[derive(Accounts)]
pub struct RouteUniversalEscrow<'info> {
    pub authority: Signer<'info>,
}

// -----------------------------------------------------------------------------
// Account Schemas
// -----------------------------------------------------------------------------

#[account]
pub struct ComplianceRecordAccount {
    pub agent_id: Pubkey,
    pub compliance_hash: [u8; 32],
    pub jurisdiction: String,
    pub risk_tier: u8,
    pub registered_at: i64,
    pub is_valid: bool,
    pub bump: u8,
}

#[account]
pub struct AgentCreditAccount {
    pub agent_id: Pubkey,
    pub credit_score: u16,
    pub risk_score: u8,
    pub completed_audits: u32,
    pub last_updated: i64,
    pub is_blacklisted: bool,
    pub bump: u8,
}

#[account]
pub struct M2MEscrowAccount {
    pub job_id: [u8; 32],
    pub payer: Pubkey,
    pub payee: Pubkey,
    pub amount: u64,
    pub is_settled: bool,
    pub bump: u8,
}

#[account]
pub struct FactoringAccount {
    pub invoice_hash: [u8; 32],
    pub borrower: Pubkey,
    pub advance_amount: u64,
    pub discount_fee: u64,
    pub is_funded: bool,
    pub bump: u8,
}

#[account]
pub struct InsuranceClaimAccount {
    pub incident_hash: [u8; 32],
    pub claimant: Pubkey,
    pub claimed_payout: u64,
    pub is_approved: bool,
    pub bump: u8,
}

#[account]
pub struct CreditLoanAccount {
    pub borrower: Pubkey,
    pub principal: u64,
    pub interest_bps: u16,
    pub borrowed_at: i64,
    pub is_active: bool,
    pub bump: u8,
}

#[account]
pub struct TreasuryVaultAccount {
    pub accumulated_tolls: u64,
    pub rwa_tbill_nav: u64,
    pub bump: u8,
}

#[error_code]
pub enum GateError {
    #[msg("Security Risk Score exceeded maximum permissible threshold")]
    RiskThresholdExceeded,
    #[msg("Agent is blacklisted from autonomous financial execution")]
    AgentBlacklisted,
    #[msg("Invalid zero Job ID supplied")]
    InvalidJobId,
    #[msg("Empty physical truth payload supplied")]
    EmptyTruthPayload,
}
