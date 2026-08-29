"""
Enterprise API Key & Rate Limit SLA Manager for Agent Security Gate x402.
Supports B2B institutional keys, custom SLA tiers, and strict in-memory rate limiting.
"""

import time
import secrets
import threading
from typing import Dict, Optional, Tuple
from pydantic import BaseModel
from app.schemas import PricingTier


class EnterpriseKeyRecord(BaseModel):
    organization_name: str
    contact_email: str
    api_key: str
    tier: PricingTier
    rate_limit_rpm: int
    is_active: bool = True
    created_at_utc: str
    request_timestamps: list[float] = []


class EnterpriseManager:
    """Thread-safe manager for enterprise API keys and rate limits."""

    def __init__(self):
        self._lock = threading.Lock()
        self._keys: Dict[str, EnterpriseKeyRecord] = {}
        self._seed_demo_enterprise_key()

    def _seed_demo_enterprise_key(self):
        now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        demo_key = "sec_live_enterprise_demo_gate_2026"
        self._keys[demo_key] = EnterpriseKeyRecord(
            organization_name="AI Agent Security Foundation (Demo)",
            contact_email="enterprise@agentsecurity.org",
            api_key=demo_key,
            tier=PricingTier.ENTERPRISE,
            rate_limit_rpm=3000,
            is_active=True,
            created_at_utc=now_iso,
            request_timestamps=[]
        )

    def create_key(self, org_name: str, email: str, tier: PricingTier = PricingTier.ENTERPRISE) -> EnterpriseKeyRecord:
        rpm = 3000 if tier == PricingTier.ENTERPRISE else 300
        now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        api_key = f"sec_live_{secrets.token_urlsafe(24)}"
        
        record = EnterpriseKeyRecord(
            organization_name=org_name,
            contact_email=email,
            api_key=api_key,
            tier=tier,
            rate_limit_rpm=rpm,
            is_active=True,
            created_at_utc=now_iso,
            request_timestamps=[]
        )
        with self._lock:
            self._keys[api_key] = record
        return record

    def verify_key(self, api_key: str) -> Tuple[bool, str, Optional[EnterpriseKeyRecord]]:
        """
        Verifies API key validity and checks against sliding window rate limit.
        Returns: (is_allowed: bool, reason: str, record: Optional[EnterpriseKeyRecord])
        """
        now = time.time()
        with self._lock:
            record = self._keys.get(api_key)
            if not record:
                return False, "Invalid API Key.", None
            if not record.is_active:
                return False, "API Key is deactivated.", None

            # Sliding window 60s rate limit filter
            window_start = now - 60.0
            record.request_timestamps = [t for t in record.request_timestamps if t > window_start]

            if len(record.request_timestamps) >= record.rate_limit_rpm:
                return False, f"Rate limit exceeded ({record.rate_limit_rpm} RPM).", record

            record.request_timestamps.append(now)
            return True, "Authorized", record


enterprise_manager = EnterpriseManager()
