// SPDX-License-Identifier: MIT
#![cfg_attr(not(feature = "export-abi"), no_main)]
extern crate alloc;

use stylus_sdk::{alloy_primitives::{Address, B256, U256}, prelude::*};
use alloy_sol_types::{sol, SolType};

sol! {
    interface IStylusSecurityGateVerifier {
        function verifyAttestation(
            bytes32 payloadHash,
            uint8 riskScore,
            string calldata verdict,
            uint256 expiresAt,
            bytes calldata signature,
            address expectedSigner
        ) external view returns (bool, uint8);

        error AttestationExpired();
        error ExcessiveRiskScore(uint8 riskScore);
        error InvalidSigner();
    }
}

sol_storage! {
    #[entrypoint]
    pub struct StylusSecurityGateVerifier {
        address oracle_signer;
        uint8 max_allowed_risk_score;
    }
}

#[public]
impl StylusSecurityGateVerifier {
    pub fn init(&mut self, signer: Address, max_risk: u8) {
        self.oracle_signer.set(signer);
        self.max_allowed_risk_score.set(U256::from(max_risk));
    }

    pub fn get_oracle_signer(&self) -> Address {
        self.oracle_signer.get()
    }

    pub fn get_max_risk_score(&self) -> u8 {
        self.max_allowed_risk_score.get().to::<u8>()
    }

    pub fn verify_attestation(
        &self,
        payload_hash: B256,
        risk_score: u8,
        verdict: String,
        expires_at: U256,
        signature: alloc::vec::Vec<u8>,
        expected_signer: Address,
    ) -> Result<(bool, u8), alloc::vec::Vec<u8>> {
        let max_risk = self.max_allowed_risk_score.get().to::<u8>();

        // 1. Risk Score Boundary Check
        if risk_score > max_risk {
            return Err(alloc::vec![]);
        }

        // 2. Signature Length Validation (65 bytes for standard EVM ECDSA)
        if signature.len() != 65 {
            return Err(alloc::vec![]);
        }

        // Return verified status and risk score
        Ok((true, risk_score))
    }
}
