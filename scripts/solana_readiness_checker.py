"""
Solana Mainnet & Devnet Deployment Readiness Inspector.
Monitors deployer wallet balances, RPC connectivity, Anchor workspace integrity,
and provides step-by-step guidance for one-click Solana activation.
"""

import os
import sys
import json
import urllib.request

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

RPC_MAINNET = "https://api.mainnet-beta.solana.com"
RPC_DEVNET = "https://api.devnet.solana.com"
TREASURY_PUBKEY = os.getenv("SOLANA_WALLET_ADDRESS", "411ksMz9RHYVtVMe6RUUErzZYtrU9zzvkgzswKbqx9qp")
ESTIMATED_RENT_SOL = 1.85  # ~2 programs rent-exemption + tx fees

def get_solana_balance(rpc_url: str, pubkey: str) -> float:
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getBalance",
        "params": [pubkey, {"commitment": "confirmed"}]
    }
    req = urllib.request.Request(
        rpc_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            lamports = data.get("result", {}).get("value", 0)
            return lamports / 1_000_000_000.0
    except Exception as e:
        print(f"  [!] RPC Request Error ({rpc_url}): {e}")
        return 0.0

def main():
    print("=" * 65)
    print("⚡ A.GRID SOLANA ON-CHAIN DEPLOYMENT READINESS INSPECTOR")
    print("=" * 65)

    print(f"\n[1] Deployer / Treasury Public Key:")
    print(f"    Pubkey: {TREASURY_PUBKEY}")

    mainnet_bal = get_solana_balance(RPC_MAINNET, TREASURY_PUBKEY)
    print(f"\n[2] Current Solana Mainnet Balance:")
    print(f"    Balance : {mainnet_bal:.6f} SOL")
    print(f"    Required: ~{ESTIMATED_RENT_SOL:.2f} SOL (BPF Rent-Exemption for 2 Programs)")

    if mainnet_bal >= ESTIMATED_RENT_SOL:
        print(f"    Status  : ✅ READY FOR MAINNET DEPLOYMENT!")
        print(f"    Action  : Run '.github/workflows/solana-deploy.yml' with cluster='mainnet'")
    else:
        deficit = ESTIMATED_RENT_SOL - mainnet_bal
        print(f"    Status  : ⏳ INSUFFICIENT FOR MAINNET DEPLOY")
        print(f"    Deficit : ~{deficit:.4f} SOL needed to deploy on Mainnet.")
        print(f"    Guide   : Transfer ~{deficit:.2f} SOL to '{TREASURY_PUBKEY}'.")

    print("\n[3] Anchor Workspace Configuration Integrity:")
    cargo_root = os.path.exists("contracts/solana/Cargo.toml")
    escrow_cargo = os.path.exists("contracts/solana/programs/universal_escrow/Cargo.toml")
    gate_cargo = os.path.exists("contracts/solana/programs/agent_security_gate/Cargo.toml")
    gh_action = os.path.exists(".github/workflows/solana-deploy.yml")

    print(f"    - contracts/solana/Cargo.toml                : {'✅ FOUND' if cargo_root else '❌ MISSING'}")
    print(f"    - programs/universal_escrow/Cargo.toml       : {'✅ FOUND' if escrow_cargo else '❌ MISSING'}")
    print(f"    - programs/agent_security_gate/Cargo.toml    : {'✅ FOUND' if gate_cargo else '❌ MISSING'}")
    print(f"    - .github/workflows/solana-deploy.yml        : {'✅ FOUND' if gh_action else '❌ MISSING'}")

    print("\n[4] Next Steps:")
    print("    A. Test Build & Devnet: Go to GitHub Repo -> Actions -> 'Solana Anchor Build & Deploy Pipeline' -> Run workflow (devnet).")
    print("    B. Mainnet Deployment: Once SOL is funded, add 'SOLANA_DEPLOYER_KEY' in GitHub Secrets and run workflow (mainnet).")
    print("=" * 65)

if __name__ == "__main__":
    main()
