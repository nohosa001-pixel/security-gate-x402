"""
Script to compile all Universal Escrow & Truth Adapter Solidity contracts
and output clean ABI and Bytecode JSON artifacts to contracts/abi/ directory.
"""
import json
import os
from pathlib import Path
import solcx

CONTRACTS_DIR = Path(__file__).resolve().parent.parent / "contracts"
ABI_DIR = CONTRACTS_DIR / "abi"
ABI_DIR.mkdir(parents=True, exist_ok=True)

def compile_and_export():
    installed_versions = solcx.get_installed_solc_versions()
    target_version = "0.8.20"
    if not any(str(v) == target_version for v in installed_versions):
        print(f"Installing solc {target_version}...")
        solcx.install_solc(target_version)
    solcx.set_solc_version(target_version)

    sources = {
        "ITruthAdapter.sol": {
            "content": (CONTRACTS_DIR / "ITruthAdapter.sol").read_text(encoding="utf-8")
        },
        "TruthAdapter.sol": {
            "content": (CONTRACTS_DIR / "TruthAdapter.sol").read_text(encoding="utf-8")
        },
        "UniversalEscrowCore.sol": {
            "content": (CONTRACTS_DIR / "UniversalEscrowCore.sol").read_text(encoding="utf-8")
        }
    }

    input_json = {
        "language": "Solidity",
        "sources": sources,
        "settings": {
            "viaIR": True,
            "optimizer": {
                "enabled": True,
                "runs": 200
            },
            "outputSelection": {
                "*": {
                    "*": ["abi", "evm.bytecode", "metadata"]
                }
            }
        }
    }

    print("Compiling contracts with viaIR enabled...")
    compiled = solcx.compile_standard(input_json)
    
    contracts_compiled = compiled.get("contracts", {})
    for source_file, contracts_dict in contracts_compiled.items():
        for contract_name, artifact in contracts_dict.items():
            abi = artifact.get("abi", [])
            bytecode = artifact.get("evm", {}).get("bytecode", {}).get("object", "")
            
            output_file = ABI_DIR / f"{contract_name}.json"
            output_data = {
                "contractName": contract_name,
                "sourceFile": source_file,
                "compiler": f"solc-{target_version}",
                "abi": abi,
                "bytecode": bytecode
            }
            output_file.write_text(json.dumps(output_data, indent=2), encoding="utf-8")
            print(f"[OK] Generated artifact: {output_file.name} (ABI methods: {len(abi)})")

    print("\nAll Universal Escrow contracts compiled and finalized successfully!")

if __name__ == "__main__":
    compile_and_export()
