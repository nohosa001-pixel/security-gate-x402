"""
Active Live Cybersecurity, AI-Security & Finance/Stablecoin Intelligence Ingestor
for agent-security-gate-x402 Brain.
Collects real-time CISA advisories, AI/smart-contract security threats, institutional finance/DeFi
headlines, and live USDC peg telemetry on every 30-minute Cloud Scheduler cycle.
"""

from __future__ import annotations

import hashlib
import json
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

SECURITY_FINANCE_FEEDS = [
    (
        "CISA_CYBER_ADVISORIES",
        "SECURITY",
        "https://www.cisa.gov/cybersecurity-advisories/all.xml",
    ),
    (
        "AI_AND_WEB3_SECURITY",
        "SECURITY",
        "https://news.google.com/rss/search?q=(%22prompt+injection%22+OR+%22smart+contract+exploit%22+OR+%22DeFi+hack%22+OR+%22AI+agent+security%22)&hl=en-US&gl=US&ceid=US:en",
    ),
    (
        "STABLECOIN_AND_FINANCE_RISK",
        "FINANCE",
        "https://news.google.com/rss/search?q=(USDC+OR+stablecoin+OR+%22liquidity+risk%22+OR+%22settlement+risk%22+OR+%22central+bank%22)+finance&hl=en-US&gl=US&ceid=US:en",
    ),
]


def _fetch_usdc_peg_usd(timeout_sec: float = 4.0) -> Optional[float]:
    """Fetches live USDC/USD peg price from CoinGecko/DeFiLlama public endpoint."""
    try:
        req = urllib.request.Request(
            "https://coins.llama.fi/prices/current/coingecko:usd-coin",
            headers={"User-Agent": "AGRID-SecurityGate-Brain/3.0"},
        )
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            price = (data.get("coins") or {}).get("coingecko:usd-coin", {}).get("price")
            if price is not None:
                return round(float(price), 5)
    except Exception:
        pass
    return None


def collect_live_security_and_finance_intel(cycle_num: int = 1, timeout_sec: float = 5.0) -> Dict[str, Any]:
    """Actively collects live Security & Finance RSS items plus live USDC settlement peg telemetry."""
    feed_name, category, feed_url = SECURITY_FINANCE_FEEDS[cycle_num % len(SECURITY_FINANCE_FEEDS)]
    now_iso = datetime.now(timezone.utc).isoformat()

    items: List[Dict[str, str]] = []
    rss_source = "FALLBACK"
    try:
        req = urllib.request.Request(feed_url, headers={"User-Agent": "AGRID-SecurityGate-Brain/3.0"})
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            raw_xml = resp.read().decode("utf-8", errors="replace")
        root = ET.fromstring(raw_xml)
        for elem in root.findall(".//item")[:3]:
            title = (elem.findtext("title") or "").strip()
            pub = (elem.findtext("pubDate") or "").strip()
            link = (elem.findtext("link") or "").strip()
            if title:
                items.append({
                    "category": category,
                    "feed": feed_name,
                    "title": title[:180],
                    "published": pub[:64],
                    "link": link[:240],
                    "hash": "0x" + hashlib.sha256(title.encode("utf-8")).hexdigest()[:16],
                })
        if items:
            rss_source = f"LIVE_RSS:{feed_name}"
    except Exception:
        pass

    usdc_peg = _fetch_usdc_peg_usd(timeout_sec=4.0)
    peg_status = "NOMINAL"
    if usdc_peg is not None and abs(usdc_peg - 1.0) >= 0.01:
        peg_status = "DEPEG_ALERT"

    samples_added = len(items) + (1 if usdc_peg is not None else 0)
    return {
        "observed_at_utc": now_iso,
        "category": category,
        "feed": feed_name,
        "rss_source": rss_source,
        "live_samples_added": samples_added,
        "items": items,
        "finance_settlement_monitor": {
            "token": "USDC",
            "price_usd": usdc_peg,
            "peg_status": peg_status,
            "source": "LIVE_DEFILLAMA_COINS" if usdc_peg is not None else "FALLBACK",
        },
    }
