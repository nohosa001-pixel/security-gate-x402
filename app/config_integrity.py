"""
Config Integrity & Anti-Tamper Module (Sentinel Defense).
Computes cryptographic SHA-256 baselines of critical configuration objects,
wallet limits, allowlists, and environment variables. Detects memory tampering
or unauthorized runtime config modifications, triggering immediate Fail-Closed lockdown.
"""

import hashlib
import json
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


class ConfigTamperError(Exception):
    """Raised when in-memory or on-disk configuration tampering is detected."""
    pass


@dataclass(frozen=True)
class ConfigSeal:
    baseline_hash: str
    sealed_at: float
    keys_sealed: tuple


def hash_config_dict(config: Dict[str, Any]) -> str:
    """Computes a deterministic SHA-256 hash of sorted key-value pairs."""
    sorted_items = sorted(config.items(), key=lambda x: x[0])
    serialized = "::".join(f"{k}={json.dumps(v, sort_keys=True, default=str)}" for k, v in sorted_items)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def seal_config(config: Dict[str, Any]) -> ConfigSeal:
    """Creates an immutable baseline seal of the provided configuration dictionary."""
    baseline_hash = hash_config_dict(config)
    return ConfigSeal(
        baseline_hash=baseline_hash,
        sealed_at=time.time(),
        keys_sealed=tuple(sorted(config.keys())),
    )


def verify_config_integrity(
    seal: ConfigSeal,
    current_config: Dict[str, Any],
    raise_on_tamper: bool = False,
) -> Dict[str, Any]:
    """
    Verifies live runtime configuration against the baseline seal.
    Returns status dict and optionally raises ConfigTamperError if tampered.
    """
    current_hash = hash_config_dict(current_config)
    if current_hash == seal.baseline_hash:
        return {
            "is_valid": True,
            "status": "OK",
            "tampered_keys": [],
            "message": "Configuration integrity intact.",
        }

    # Identify modified or missing keys
    tampered_keys: List[str] = []
    for key in seal.keys_sealed:
        if key not in current_config:
            tampered_keys.append(f"{key} (deleted)")

    if not tampered_keys and current_hash != seal.baseline_hash:
        tampered_keys.append("configuration_values_altered")

    error_msg = (
        f"🚨 [FAIL-CLOSED] Configuration tampering detected! "
        f"Expected seal {seal.baseline_hash[:12]}..., got {current_hash[:12]}... "
        f"Tampered items: {', '.join(tampered_keys)}"
    )

    if raise_on_tamper:
        raise ConfigTamperError(error_msg)

    return {
        "is_valid": False,
        "status": "TAMPER_DETECTED",
        "tampered_keys": tampered_keys,
        "message": error_msg,
    }
