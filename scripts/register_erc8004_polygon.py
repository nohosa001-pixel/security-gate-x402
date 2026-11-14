"""Register A.GRID on Polygon Mainnet or Amoy ERC-8004 IdentityRegistry.

Usage:
  .venv\\Scripts\\python scripts/register_erc8004_polygon.py --network polygon-mainnet
  .venv\\Scripts\\python scripts/register_erc8004_polygon.py --network polygon-mainnet --broadcast
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from app.erc8004_registry import (
    DEFAULT_HUB_BASE_URL,
    ERC8004_DEPLOYMENTS,
    build_agrid_registration_json,
    build_register_calldata,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Register A.GRID on Polygon ERC-8004 IdentityRegistry")
    parser.add_argument("--network", default="polygon-mainnet", choices=list(ERC8004_DEPLOYMENTS.keys()))
    parser.add_argument(
        "--agent-uri",
        default=f"{DEFAULT_HUB_BASE_URL}/.well-known/erc8004-registration.json",
        help="Public HTTPS or IPFS URI serving the ERC-8004 registration JSON",
    )
    parser.add_argument("--broadcast", action="store_true", help="Sign and broadcast tx using EVM_PRIVATE_KEY")
    args = parser.parse_args()

    reg_doc = build_agrid_registration_json()
    tx_spec = build_register_calldata(agent_uri=args.agent_uri, network=args.network)

    print("=== A.GRID ERC-8004 Registration Preview ===")
    print(json.dumps({"tx_spec": tx_spec, "services": reg_doc["services"]}, indent=2))

    if not args.broadcast:
        print("\n[DRY-RUN] Re-run with --broadcast and DEPLOYER_PRIVATE_KEY / EVM_PRIVATE_KEY set to mint on-chain.")
        return 0

    from dotenv import load_dotenv

    load_dotenv(WORKSPACE_ROOT / ".env")
    priv_key = (
        os.getenv("EVM_PRIVATE_KEY")
        or os.getenv("PRIVATE_KEY")
        or os.getenv("DEPLOYER_PRIVATE_KEY")
        or os.getenv("GATE_PRIVATE_KEY")
    )
    if not priv_key:
        print("[ERROR] EVM_PRIVATE_KEY, PRIVATE_KEY, or DEPLOYER_PRIVATE_KEY is required for --broadcast.")
        return 1

    from web3 import Web3

    cfg = ERC8004_DEPLOYMENTS[args.network]
    w3 = Web3(Web3.HTTPProvider(cfg["rpc_url"]))
    if not w3.is_connected():
        print(f"[ERROR] Failed to connect to RPC: {cfg['rpc_url']}")
        return 1

    account = w3.eth.account.from_key(priv_key)
    tx = {
        "chainId": cfg["chain_id"],
        "from": account.address,
        "to": Web3.to_checksum_address(tx_spec["to"]),
        "value": 0,
        "data": tx_spec["data"],
        "nonce": w3.eth.get_transaction_count(account.address),
        "gasPrice": w3.eth.gas_price,
    }
    tx["gas"] = int(w3.eth.estimate_gas(tx) * 1.2)
    signed = w3.eth.account.sign_transaction(tx, priv_key)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    print(f"[SENT] tx_hash={tx_hash.hex()}")
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
    print(f"[CONFIRMED] status={receipt['status']} block={receipt['blockNumber']}")
    return 0 if receipt["status"] == 1 else 1


if __name__ == "__main__":
    raise SystemExit(main())

