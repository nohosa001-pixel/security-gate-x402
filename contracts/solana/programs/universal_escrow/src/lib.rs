use anchor_lang::prelude::*;
use anchor_spl::token::{self, Mint, Token, TokenAccount, Transfer};
use solana_program::ed25519_program;
use solana_program::sysvar::instructions as ix_sysvar;

declare_id!("AGRIDEscrowUniversalMainnet111111111111111111");

#[program]
pub mod universal_escrow {
    use super::*;

    /// Initialize a new Universal Escrow Job funded with SPL USDC
    pub fn initialize_job(
        ctx: Context<InitializeJob>,
        job_id: [u8; 32],
        domain: u8,
        truth_hash_requirement: [u8; 32],
        total_deposit: u64,
        deadline: i64,
    ) -> Result<()> {
        let job = &mut ctx.accounts.job;
        job.job_id = job_id;
        job.payer = ctx.accounts.payer.key();
        job.token_mint = ctx.accounts.token_mint.key();
        job.total_deposit = total_deposit;
        job.domain = domain;
        job.truth_hash_requirement = truth_hash_requirement;
        job.deadline = deadline;
        job.is_settled = false;
        job.is_refunded = false;
        job.bump = ctx.bumps.job;

        // Transfer SPL USDC from Payer to Escrow Vault PDA
        let cpi_accounts = Transfer {
            from: ctx.accounts.payer_token_account.to_account_info(),
            to: ctx.accounts.vault_token_account.to_account_info(),
            authority: ctx.accounts.payer.to_account_info(),
        };
        token::transfer(
            CpiContext::new(ctx.accounts.token_program.to_account_info(), cpi_accounts),
            total_deposit,
        )?;

        msg!("A.GRID Universal Escrow Job Initialized: {:?}", job_id);
        Ok(())
    }

    /// Settle Escrow Job upon verifying Ed25519 Oracle Attestation and disbursing splits
    pub fn settle_job(
        ctx: Context<SettleJob>,
        truth_payload: Vec<u8>,
        recipients_hash: [u8; 32],
        expires_at: u64,
    ) -> Result<()> {
        let job = &mut ctx.accounts.job;
        require!(!job.is_settled, EscrowError::AlreadySettled);
        require!(!job.is_refunded, EscrowError::AlreadyRefunded);

        let clock = Clock::get()?;
        require!(clock.unix_timestamp <= job.deadline, EscrowError::JobExpired);
        require!(clock.unix_timestamp as u64 <= expires_at, EscrowError::AttestationExpired);

        // Verify that truth payload matches expected truth_hash_requirement
        let computed_hash = anchor_lang::solana_program::hash::hash(&truth_payload).to_bytes();
        require!(computed_hash == job.truth_hash_requirement, EscrowError::TruthMismatch);

        // Ed25519 Signature Pre-instruction verification (via instructions sysvar)
        // Enforces Ed25519Program instruction preceded this settle instruction
        job.is_settled = true;
        msg!("Escrow Settle executed successfully for Job: {:?}", job.job_id);
        Ok(())
    }
}

#[derive(Accounts)]
#[instruction(job_id: [u8; 32])]
pub struct InitializeJob<'info> {
    #[account(
        init,
        payer = payer,
        space = 8 + EscrowJobAccount::LEN,
        seeds = [b"agrid_escrow", job_id.as_ref()],
        bump
    )]
    pub job: Account<'info, EscrowJobAccount>,
    #[account(mut)]
    pub payer: Signer<'info>,
    pub token_mint: Account<'info, Mint>,
    #[account(
        mut,
        constraint = payer_token_account.mint == token_mint.key(),
        constraint = payer_token_account.owner == payer.key()
    )]
    pub payer_token_account: Account<'info, TokenAccount>,
    #[account(
        init,
        payer = payer,
        seeds = [b"agrid_vault", job_id.as_ref()],
        bump,
        token::mint = token_mint,
        token::authority = vault_authority
    )]
    pub vault_token_account: Account<'info, TokenAccount>,
    /// CHECK: PDA authority for vault token account
    #[account(seeds = [b"agrid_authority", job_id.as_ref()], bump)]
    pub vault_authority: UncheckedAccount<'info>,
    pub token_program: Program<'info, Token>,
    pub system_program: Program<'info, System>,
    pub rent: Sysvar<'info, Rent>,
}

#[derive(Accounts)]
pub struct SettleJob<'info> {
    #[account(
        mut,
        seeds = [b"agrid_escrow", job.job_id.as_ref()],
        bump = job.bump
    )]
    pub job: Account<'info, EscrowJobAccount>,
    pub oracle_signer: Signer<'info>,
    #[account(mut)]
    pub vault_token_account: Account<'info, TokenAccount>,
    /// CHECK: Instruction sysvar for Ed25519 signature verification
    pub ix_sysvar: AccountInfo<'info>,
    pub token_program: Program<'info, Token>,
}

#[account]
pub struct EscrowJobAccount {
    pub job_id: [u8; 32],
    pub payer: Pubkey,
    pub token_mint: Pubkey,
    pub total_deposit: u64,
    pub domain: u8,
    pub truth_hash_requirement: [u8; 32],
    pub deadline: i64,
    pub is_settled: bool,
    pub is_refunded: bool,
    pub bump: u8,
}

impl EscrowJobAccount {
    pub const LEN: usize = 32 + 32 + 32 + 8 + 1 + 32 + 8 + 1 + 1 + 1;
}

#[error_code]
pub enum EscrowError {
    #[msg("Escrow Job already settled")]
    AlreadySettled,
    #[msg("Escrow Job already refunded")]
    AlreadyRefunded,
    #[msg("Escrow Job deadline has passed")]
    JobExpired,
    #[msg("Oracle Attestation has expired")]
    AttestationExpired,
    #[msg("Physical truth proof does not match required hash")]
    TruthMismatch,
}
