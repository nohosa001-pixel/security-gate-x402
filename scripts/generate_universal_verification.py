"""
Generates verification artifacts (Standard-Json-Input and Flattened Solidity)
for UniversalEscrowCore and TruthAdapter across Polygon, Base, and Arbitrum.
"""
import json
import os
from pathlib import Path
from eth_abi import encode

ROOT_DIR = Path(__file__).resolve().parent.parent
CONTRACTS_DIR = ROOT_DIR / "contracts"
VERIFY_DIR = CONTRACTS_DIR / "verification"
VERIFY_DIR.mkdir(parents=True, exist_ok=True)

DEPLOYER = "0x255F9991233f86B29dB847c8d5b8CB9915e80dCf"

def generate_standard_json():
    itruth_src = (CONTRACTS_DIR / "ITruthAdapter.sol").read_text(encoding="utf-8")
    truth_src = (CONTRACTS_DIR / "TruthAdapter.sol").read_text(encoding="utf-8")
    escrow_src = (CONTRACTS_DIR / "UniversalEscrowCore.sol").read_text(encoding="utf-8")

    # 1. UniversalEscrowCore Standard-Json-Input
    escrow_standard = {
        "language": "Solidity",
        "sources": {
            "ITruthAdapter.sol": {"content": itruth_src},
            "UniversalEscrowCore.sol": {"content": escrow_src}
        },
        "settings": {
            "optimizer": {
                "enabled": True,
                "runs": 200
            },
            "viaIR": True,
            "outputSelection": {
                "*": {
                    "*": ["abi", "evm.bytecode"]
                }
            }
        }
    }
    escrow_json_path = VERIFY_DIR / "UniversalEscrowCore.standard.json"
    escrow_json_path.write_text(json.dumps(escrow_standard, indent=2), encoding="utf-8")
    print(f"[OK] Generated {escrow_json_path.name}")

    # 2. TruthAdapter Standard-Json-Input
    truth_standard = {
        "language": "Solidity",
        "sources": {
            "ITruthAdapter.sol": {"content": itruth_src},
            "TruthAdapter.sol": {"content": truth_src}
        },
        "settings": {
            "optimizer": {
                "enabled": True,
                "runs": 200
            },
            "viaIR": True,
            "outputSelection": {
                "*": {
                    "*": ["abi", "evm.bytecode"]
                }
            }
        }
    }
    truth_json_path = VERIFY_DIR / "TruthAdapter.standard.json"
    truth_json_path.write_text(json.dumps(truth_standard, indent=2), encoding="utf-8")
    print(f"[OK] Generated {truth_json_path.name}")

    # 3. Flattened UniversalEscrowCore.sol
    # Since UniversalEscrowCore imports ./ITruthAdapter.sol, inline ITruthAdapter
    escrow_flattened = "// SPDX-License-Identifier: MIT\npragma solidity ^0.8.20;\n\n"
    # Extract interface part (omit license/pragma)
    itruth_body = "\n".join(
        line for line in itruth_src.splitlines() 
        if not line.startswith("// SPDX-License-Identifier") and not line.startswith("pragma solidity")
    ).strip()
    escrow_body = "\n".join(
        line for line in escrow_src.splitlines() 
        if not line.startswith("// SPDX-License-Identifier") and not line.startswith("pragma solidity") and not line.startswith('import "./ITruthAdapter.sol";')
    ).strip()
    full_escrow_flattened = escrow_flattened + itruth_body + "\n\n" + escrow_body + "\n"
    (VERIFY_DIR / "UniversalEscrowCore.flattened.sol").write_text(full_escrow_flattened, encoding="utf-8")
    print(f"[OK] Generated UniversalEscrowCore.flattened.sol")

    # 4. Flattened TruthAdapter.sol
    truth_body = "\n".join(
        line for line in truth_src.splitlines() 
        if not line.startswith("// SPDX-License-Identifier") and not line.startswith("pragma solidity") and not line.startswith('import "./ITruthAdapter.sol";')
    ).strip()
    full_truth_flattened = escrow_flattened + itruth_body + "\n\n" + truth_body + "\n"
    (VERIFY_DIR / "TruthAdapter.flattened.sol").write_text(full_truth_flattened, encoding="utf-8")
    print(f"[OK] Generated TruthAdapter.flattened.sol")

    # 5. Constructor Arguments Hex
    escrow_args = encode(["address", "address"], [DEPLOYER, DEPLOYER]).hex()
    truth_args = encode(["address", "uint8"], [DEPLOYER, 0]).hex()
    
    print("\n--- Constructor Arguments (ABI-encoded Hex) ---")
    print(f"UniversalEscrowCore: {escrow_args}")
    print(f"TruthAdapter:        {truth_args}")

if __name__ == "__main__":
    generate_standard_json()
