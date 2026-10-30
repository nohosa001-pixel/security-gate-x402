"""
Script to compile all Universal Escrow, V2 Agentic Shield Pool, and Logistics PoD Solidity contracts
and output clean ABI and Bytecode JSON artifacts to contracts/abi/ directory.
"""
import sys
import json
import os
from pathlib import Path
import solcx

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT_DIR = Path(__file__).resolve().parent.parent
CONTRACTS_DIR = ROOT_DIR / "contracts"
ABI_DIR = CONTRACTS_DIR / "abi"
ABI_DIR.mkdir(parents=True, exist_ok=True)


def ensure_solc_installed(version: str):
    installed_versions = solcx.get_installed_solc_versions()
    if not any(str(v) == version for v in installed_versions):
        print(f"Installing solc {version}...")
        solcx.install_solc(version)


def compile_v1_universal_escrow():
    target_version = "0.8.20"
    ensure_solc_installed(target_version)

    sources = {
        "ITruthAdapter.sol": {
            "content": (CONTRACTS_DIR / "ITruthAdapter.sol").read_text(encoding="utf-8")
        },
        "TruthAdapter.sol": {
            "content": (CONTRACTS_DIR / "TruthAdapter.sol").read_text(encoding="utf-8")
        },
        "UniversalEscrowCore.sol": {
            "content": (CONTRACTS_DIR / "UniversalEscrowCore.sol").read_text(encoding="utf-8")
        },
        "SecurityGateOMSPolicy.sol": {
            "content": (CONTRACTS_DIR / "SecurityGateOMSPolicy.sol").read_text(encoding="utf-8")
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

    print("\n📦 Compiling UniversalEscrowCore & Truth Adapters (solc 0.8.20 viaIR)...")
    compiled = solcx.compile_standard(input_json, solc_version=target_version)
    _export_artifacts(compiled, target_version)


def compile_v2_shield_and_logistics():
    target_version = "0.8.24"
    ensure_solc_installed(target_version)

    sources = {
        "LogisticsPoDEscrow.sol": {
            "content": (CONTRACTS_DIR / "LogisticsPoDEscrow.sol").read_text(encoding="utf-8")
        },
        "AgenticShieldPool.sol": {
            "content": (CONTRACTS_DIR / "AgenticShieldPool.sol").read_text(encoding="utf-8")
        }
    }

    input_json = {
        "language": "Solidity",
        "sources": sources,
        "settings": {
            "evmVersion": "cancun",
            "remappings": [
                "@openzeppelin/=node_modules/@openzeppelin/"
            ],
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

    print("\n📦 Compiling AgenticShieldPool & LogisticsPoDEscrow (solc 0.8.24 Cancun + OZ 5)...")
    compiled = solcx.compile_standard(
        input_json,
        solc_version=target_version,
        base_path=str(ROOT_DIR)
    )
    _export_artifacts(compiled, target_version)


def _export_artifacts(compiled: dict, compiler_version: str):
    contracts_compiled = compiled.get("contracts", {})
    for source_file, contracts_dict in contracts_compiled.items():
        for contract_name, artifact in contracts_dict.items():
            abi = artifact.get("abi", [])
            bytecode = artifact.get("evm", {}).get("bytecode", {}).get("object", "")

            output_file = ABI_DIR / f"{contract_name}.json"
            output_data = {
                "contractName": contract_name,
                "sourceFile": source_file,
                "compiler": f"solc-{compiler_version}",
                "abi": abi,
                "bytecode": bytecode
            }
            output_file.write_text(json.dumps(output_data, indent=2), encoding="utf-8")
            print(f"  [OK] Generated artifact: {output_file.name} (ABI methods: {len(abi)})")


def compile_all():
    print("=" * 70)
    print("  [A.GRID] Full Contract Suite Compiler & Artifact Exporter")
    print("=" * 70)
    compile_v1_universal_escrow()
    compile_v2_shield_and_logistics()
    print("\n✅ All contract ABI and Bytecode artifacts generated in contracts/abi/ successfully!")


if __name__ == "__main__":
    compile_all()
