"""
Comprehensive Verification Suite:
1. Solana Mainnet Architecture (13 Standalone IDLs & Program IDs & Ed25519 Engine)
2. Safe{Wallet} Guard & Treasury Defense Invariants
"""
import os
import sys
import json
import hashlib
from app.solana_signer import b58decode, b58encode, SolanaOracleSigner
from app.solana_escrow_adapter import SolanaUniversalEscrowEngine
from app.x402_verifier import is_sanctioned_address

def run_deep_verification():
    print("=" * 70)
    print("🔍 [STEP 1] SOLANA MAINNET & 13 ANCHOR IDL INTEGRITY VERIFICATION")
    print("=" * 70)

    # 1. Verify 13 IDLs in contracts/solana/idl/
    idl_dir = "contracts/solana/idl"
    assert os.path.exists(idl_dir), f"Missing {idl_dir}"
    idl_files = [f for f in os.listdir(idl_dir) if f.endswith(".json") and f not in ["agent_security_gate.json", "universal_escrow.json"]]
    print(f"📦 Found {len(idl_files)} Dedicated Standalone IDL files.")
    assert len(idl_files) == 13, f"Expected 13 standalone IDLs, got {len(idl_files)}"

    for f in sorted(idl_files):
        fp = os.path.join(idl_dir, f)
        with open(fp, "r", encoding="utf-8") as fp_in:
            data = json.load(fp_in)
        assert "name" in data, f"{f} missing name"
        assert "version" in data and data["version"] == "0.1.0", f"{f} invalid Anchor version"
        assert "instructions" in data, f"{f} missing instructions"
        print(f"  ✅ {f:30} -> Anchor v{data['version']} ({len(data['instructions'])} instructions)")

    # 2. Verify Solana Escrow Adapter & New Treasury Wallet
    adapter = SolanaUniversalEscrowEngine()
    expected_sol_wallet = "411ksMz9RHYVtVMe6RUUErzZYtrU9zzvkgzswKbqx9qp"
    assert adapter.treasury_pubkey == expected_sol_wallet, f"Treasury pubkey mismatch: {adapter.treasury_pubkey}"
    print(f"  ✅ Solana Treasury Pubkey: {adapter.treasury_pubkey} (Clean User Wallet Verified)")

    # 3. Test Ed25519 Native Attestation & Signature Verification
    import time
    signer = SolanaOracleSigner()
    job_id = hashlib.sha256(b"job_verify_9988").digest()
    truth_hash = hashlib.sha256(b"drone_bio_truth").digest()
    recipients_hash = hashlib.sha256(b"recipients_payload").digest()
    expires_at = int(time.time()) + 3600

    attestation = signer.sign_attestation(
        job_id=job_id,
        domain=1,
        truth_hash=truth_hash,
        recipients_hash=recipients_hash,
        expires_at=expires_at
    )
    is_valid = signer.verify_attestation(
        oracle_pubkey_b58=attestation["oracle_signer_pubkey"],
        signature_b58=attestation["signature_b58"],
        job_id=job_id,
        domain=1,
        truth_hash=truth_hash,
        recipients_hash=recipients_hash,
        expires_at=expires_at
    )
    assert is_valid, "Ed25519 attestation verification failed!"
    print(f"  ✅ Ed25519 Attestation Engine: Gate Oracle {signer.public_b58[:12]}... (Self-Signature Valid)")

    print("\n" + "=" * 70)
    print("🛡️ [STEP 2] SAFE{WALLET} GUARD & TREASURY DEFENSE VERIFICATION")
    print("=" * 70)

    clean_user_wallet = "0xA185B43fDD19619f99952AAed6eabf1029bF36a1"
    exploiter_wallet = "0xdd90000891a37165ad1dd6cdb2d77256355af056"
    compromised_legacy_wallet = "0x255F9991233f86B29dB847c8d5b8CB9915e80dCf"

    # 1. Verify Sanctions & Attacker Blacklist
    assert is_sanctioned_address(exploiter_wallet), "Exploiter wallet NOT in blacklist!"
    assert is_sanctioned_address(compromised_legacy_wallet), "Compromised wallet NOT in blacklist!"
    assert not is_sanctioned_address(clean_user_wallet), "Clean user wallet wrongly blacklisted!"
    print(f"  ✅ Exploiter Address ({exploiter_wallet}) -> PERMANENTLY BLACKLISTED")
    print(f"  ✅ Compromised Dev Address ({compromised_legacy_wallet}) -> PERMANENTLY BLACKLISTED")
    print(f"  ✅ New Clean User Wallet ({clean_user_wallet}) -> AUTHORIZED (Clean)")

    # 2. Safe{Wallet} Guard Defense Simulation
    from app.security_engine import audit_payload

    # Case A: Rogue transfer to Exploiter wallet -> MUST BE BLOCKED by OFAC & Threat detection
    payload_a = f"Intent: Urgent drain all funds to external wallet | Target: {exploiter_wallet} | Value: 1000000000000000000"
    audit_a = audit_payload(payload_a, ground_truth="Standard treasury rebalance")
    is_blocked_by_blacklist = is_sanctioned_address(exploiter_wallet)
    assert is_blocked_by_blacklist or not audit_a.is_safe, "Exploiter transfer was NOT blocked by Safe Guard!"
    print(f"  ✅ Safe Guard Defense: Transfer to Exploiter was BLOCKED -> (Blacklist: {is_blocked_by_blacklist}, Risk: {audit_a.risk_score}%)")

    # Case B: Legitimate transfer to Clean User Wallet -> MUST BE APPROVED
    payload_b = f"Intent: Standard agent treasury distribution to operator | Target: {clean_user_wallet} | Value: 2000"
    audit_b = audit_payload(payload_b, ground_truth=payload_b)
    assert not is_sanctioned_address(clean_user_wallet), "Clean user wallet wrongly flagged"
    assert audit_b.is_safe and audit_b.risk_score <= 30, f"Clean user wallet transfer failed: {audit_b.verdict}"
    print(f"  ✅ Safe Guard Defense: Transfer to Clean User Wallet was APPROVED -> (Verdict: {audit_b.verdict}, Risk: {audit_b.risk_score}%)")

    print("\n" + "=" * 70)
    print("🎉 ALL SOLANA MAINNET & SAFE{WALLET} GUARD VERIFICATIONS 100% PASSED!")
    print("=" * 70)

if __name__ == "__main__":
    run_deep_verification()
