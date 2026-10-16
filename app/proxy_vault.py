"""Zero-Exposure Credential Proxy Vault for security-gate-x402.

Isolates real secrets (API keys, private keys, bearer tokens) from LLM context memory.
Provides synthetic reference tokens to agent runtimes and performs atomic in-memory
hot-swapping immediately before outbound transmission to authorized destinations.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any, Dict, Optional, Set, Tuple
from urllib.parse import urlparse


class ProxyVaultSecurityError(PermissionError):
    """Raised when credential injection violates destination security policy."""
    pass


class ZeroExposureProxyVault:
    """Manages synthetic token virtualization and in-memory credential injection."""

    def __init__(self, token_prefix: str = "x402_sec_ref_"):
        self.token_prefix = token_prefix
        # Mapping: synthetic_token -> (raw_secret, authorized_hosts)
        self._vault: Dict[str, Tuple[str, Set[str]]] = {}
        # Reverse mapping: raw_secret -> synthetic_token (for inbound scrub/masking)
        self._reverse_vault: Dict[str, str] = {}

    def register_credential(self, raw_secret: str, authorized_hosts: Set[str]) -> str:
        """Register a real secret with a whitelist of authorized target domains.

        Returns a deterministic synthetic reference token for the agent/LLM to use.
        """
        if not raw_secret or not raw_secret.strip():
            raise ValueError("Secret cannot be empty.")
        if not authorized_hosts:
            raise ValueError("At least one authorized host must be specified.")

        # Canonicalize hostnames (lowercase, strip ports/schemes if passed)
        clean_hosts = {self._clean_host(h) for h in authorized_hosts}

        # Deterministic synthetic token generation (non-reversible hash)
        token_digest = hashlib.sha256(raw_secret.encode("utf-8")).hexdigest()[:16]
        synthetic_token = f"{self.token_prefix}{token_digest}"

        self._vault[synthetic_token] = (raw_secret, clean_hosts)
        self._reverse_vault[raw_secret] = synthetic_token
        return synthetic_token

    def _clean_host(self, host_or_url: str) -> str:
        """Extract clean hostname from URL or host string."""
        if "://" in host_or_url:
            parsed = urlparse(host_or_url)
            return (parsed.hostname or "").lower()
        # Handle host:port
        return host_or_url.split(":")[0].strip().lower()

    def get_token_for_secret(self, raw_secret: str) -> Optional[str]:
        """Look up existing synthetic token for a given raw secret."""
        return self._reverse_vault.get(raw_secret)

    def is_synthetic_token(self, text: str) -> bool:
        """Check if a string matches synthetic token format."""
        return bool(text and text.startswith(self.token_prefix))

    def intercept_and_swap_outbound(self, target_url: str, payload: str) -> str:
        """Inspect outbound payload and atomically replace synthetic tokens with real secrets.

        Validates that the target_url is strictly whitelisted for every token present in payload.
        """
        target_host = self._clean_host(target_url)
        sanitized = payload

        # Check for any synthetic tokens present in payload
        for token, (raw_secret, allowed_hosts) in self._vault.items():
            if token in sanitized:
                # Security Check: Target host MUST be explicitly authorized
                if target_host not in allowed_hosts:
                    raise ProxyVaultSecurityError(
                        f"Egress violation: Token '{token}' is unauthorized for destination host '{target_host}'."
                    )
                # In-memory hot swap
                sanitized = sanitized.replace(token, raw_secret)

        return sanitized

    def scrub_inbound_response(self, response_text: str) -> str:
        """Mask raw secrets returned in external server responses before LLM context sees them.

        Replaces raw secrets with their corresponding synthetic tokens.
        """
        scrubbed = response_text
        for raw_secret, token in self._reverse_vault.items():
            if raw_secret in scrubbed:
                scrubbed = scrubbed.replace(raw_secret, token)
        return scrubbed

    def clear(self) -> None:
        """Wipe memory store."""
        self._vault.clear()
        self._reverse_vault.clear()
