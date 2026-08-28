"""Example 3: Direct REST API Client with Attestation Cryptographic Verification.

Shows standard HTTP integration and how downstream systems verify the EIP-191 proof-of-safety.
"""

import hashlib
import json
import sys
import httpx
from eth_account import Account
from eth_account.messages import encode_defunct

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

LIVE_GATE_URL = "https://agent-security-gate-x402-7qxtp3324q-du.a.run.app"


def verify_gate_attestation(attestation: dict, original_text: str) -> bool:
    """Cryptographically verifies that the attestation receipt was not tampered with."""
    subject_hash = attestation.get("subject_hash")
    computed_hash = hashlib.sha256(original_text.encode("utf-8")).hexdigest()
    if computed_hash != subject_hash:
        print("❌ Payload hash mismatch! Text was tampered with.")
        return False

    issuer = attestation.get("issuer")
    verdict = attestation.get("verdict")
    risk_score = attestation.get("risk_score")
    issued_at = attestation.get("issued_at")
    sig = attestation.get("signature", "")

    msg_text = f"x402-attestation:v1:{subject_hash}:{verdict}:{risk_score}:{issued_at}"

    if sig.endswith("00" * 32):
        expected_sig = "0x" + hashlib.sha256((msg_text + issuer).encode("utf-8")).hexdigest() + "00" * 32
        return sig.lower() == expected_sig.lower()
    else:
        msg_hash = encode_defunct(text=msg_text)
        recovered = Account.recover_message(msg_hash, signature=sig)
        return recovered.lower() == issuer.lower()


def main():
    print("==================================================================")
    print("🌐 [REST API DEMO] Inspecting Payload & Verifying Proof-of-Safety")
    print("==================================================================")

    agent_output = "Financial report verified: Q3 operating profit was $4,500,000."
    ground_truth = "Ledger: Q3 operating profit $4,500,000."

    with httpx.Client(base_url=LIVE_GATE_URL, timeout=10.0) as client:
        payload = {
            "agent_output": agent_output,
            "is_code": False,
            "context_ground_truth": ground_truth
        }
        
        response = client.post("/api/v1/inspect", json=payload, headers={"X-Trial": "true"})
        print(f"📡 API Status: {response.status_code}")
        
        data = response.json()
        print(f"🎯 Verdict: {data['audit']['verdict']} (Risk: {data['audit']['risk_score']})")
        print(f"🔍 Numerical Accuracy: {data['audit']['nli_verification']['is_faithful']}")
        
        attestation = data["attestation"]
        print(f"\n🔏 Issued Attestation:")
        print(f"   Issuer: {attestation['issuer']}")
        print(f"   Subject Hash: {attestation['subject_hash']}")
        print(f"   Signature: {attestation['signature']}")

        # Verify Attestation
        is_valid = verify_gate_attestation(attestation, agent_output)
        print(f"\n🛡️ Cryptographic Verification: {'✅ VALID' if is_valid else '❌ INVALID'}")


if __name__ == "__main__":
    main()
