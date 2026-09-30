"""
Official X (Twitter) Publisher for Solana Mainnet 13-Contract Launch
Publishes the announcement thread using httpx and pure-Python OAuth1.
"""

import os
import sys
import time
import hmac
import hashlib
import base64
import secrets
import urllib.parse
import httpx
from dotenv import load_dotenv

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv()

X_API_KEY = os.getenv("X_API_KEY")
X_API_SECRET = os.getenv("X_API_SECRET")
X_ACCESS_TOKEN = os.getenv("X_ACCESS_TOKEN")
X_ACCESS_TOKEN_SECRET = os.getenv("X_ACCESS_TOKEN_SECRET")

TWEETS_URL = "https://api.twitter.com/2/tweets"


def generate_oauth1_header(url: str, method: str = "POST") -> str:
    """Generates pure-Python RFC 5849 OAuth 1.0a Authorization header."""
    oauth_params = {
        "oauth_consumer_key": X_API_KEY,
        "oauth_nonce": secrets.token_hex(16),
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": str(int(time.time())),
        "oauth_token": X_ACCESS_TOKEN,
        "oauth_version": "1.0"
    }

    # Encode and sort parameters
    encoded_params = sorted([
        (urllib.parse.quote(k, safe=""), urllib.parse.quote(v, safe=""))
        for k, v in oauth_params.items()
    ])
    param_string = "&".join(f"{k}={v}" for k, v in encoded_params)

    # Signature base string
    base_parts = [
        method.upper(),
        urllib.parse.quote(url, safe=""),
        urllib.parse.quote(param_string, safe="")
    ]
    signature_base = "&".join(base_parts)

    # Signing key
    signing_key = f"{urllib.parse.quote(X_API_SECRET, safe='')}&{urllib.parse.quote(X_ACCESS_TOKEN_SECRET, safe='')}"
    
    # HMAC-SHA1
    hashed = hmac.new(signing_key.encode("utf-8"), signature_base.encode("utf-8"), hashlib.sha1)
    oauth_signature = base64.b64encode(hashed.digest()).decode("utf-8")
    oauth_params["oauth_signature"] = oauth_signature

    # Build header string
    auth_header_parts = [
        f'{urllib.parse.quote(k, safe="")}="{urllib.parse.quote(v, safe="")}"'
        for k, v in sorted(oauth_params.items())
    ]
    return "OAuth " + ", ".join(auth_header_parts)


def post_tweet(text: str, reply_to_id: str = None) -> dict:
    if not all([X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET]):
        print("❌ [ERROR] Missing Twitter API credentials in .env")
        return {"success": False, "error": "Missing credentials"}

    auth_header = generate_oauth1_header(TWEETS_URL, method="POST")
    headers = {
        "Authorization": auth_header,
        "Content-Type": "application/json"
    }
    payload = {"text": text}
    if reply_to_id:
        payload["reply"] = {"in_reply_to_tweet_id": reply_to_id}

    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(TWEETS_URL, headers=headers, json=payload)
            if resp.status_code in (200, 201):
                data = resp.json().get("data", {})
                tweet_id = data.get("id")
                print(f"✅ [TWEET SUCCESS] Tweet ID: {tweet_id}")
                print(f"🔗 URL: https://x.com/i/web/status/{tweet_id}")
                return {"success": True, "tweet_id": tweet_id, "data": data}
            else:
                print(f"❌ [TWEET FAILED] Status {resp.status_code}: {resp.text}")
                return {"success": False, "error": resp.text, "status": resp.status_code}
    except Exception as e:
        print(f"❌ [EXCEPTION] {e}")
        return {"success": False, "error": str(e)}


def publish_solana_thread():
    print("=" * 80)
    print("📢 [PUBLISHING SOLANA MAINNET 13-CONTRACT LAUNCH THREAD TO X]")
    print("=" * 80)

    tweets = [
        # Tweet 1: Headline & Solana Hook
        (
            "🚀 MAJOR MILESTONE: Agent Security Gate x402 & Universal Modular Escrow v1.4.0 is now officially LIVE on Solana Mainnet! ⚡\n\n"
            "Full architectural parity with all 13 smart contracts registered and indexed on Solscan.\n\n"
            "• 400ms finality\n"
            "• <$0.0001 gas fees\n"
            "• Zero-deficit SPL USDC micro-settlements for autonomous AI agents\n\n"
            "🧵👇 #Solana #AIAgents #Web3 #Crypto #DePIN"
        ),
        # Tweet 2: 13-Contract Architecture on Solana
        (
            "1/ Complete 13-Contract Suite Live on Solana:\n\n"
            "🛡️ EU AI Act Compliance Registry (ISO-42001)\n"
            "📊 AI Agent Credit Oracle (Deterministic scoring)\n"
            "🤝 Autonomous M2M Escrow & Invoice Factoring\n"
            "🏛️ Sovereign 100% T-Bill Treasury & Insurance Slashing\n"
            "🔍 Multi-Domain Truth Adapters (DePIN, Maritime IoT, Bio-ZK)\n\n"
            "All 13 IDLs verified on Solscan: https://solscan.io/account/AGR3W3R9pKxnuZGYrpaggfkbMKVrjoniLaGvi1voBFSC"
        ),
        # Tweet 3: Omnichain Settlement & Zero-Key Security
        (
            "2/ True Omnichain AI Agent Clearing:\n\n"
            "Polygon + Base + Arbitrum + Solana Mainnet.\n\n"
            "• Zero-deficit split disbursements in native USDC across EVM & SVM\n"
            "• Sub-millisecond AST code inspection & Ed25519 cryptographic attestations\n"
            "• Zero private keys exposed: 100% public key treasury architecture\n\n"
            "The safest bridge between Web3 finance and autonomous AI swarms."
        ),
        # Tweet 4: Live Links & Open Source
        (
            "3/ Explore the Open-Source Protocol & Live Hub:\n\n"
            "🌐 Hub: https://agent-security-gate-x402-212942243360.asia-northeast3.run.app/hub/\n"
            "📦 GitHub: https://github.com/nohosa001-pixel/security-gate-x402\n"
            "📜 Guide: https://github.com/nohosa001-pixel/security-gate-x402/blob/main/contracts/solana/SOLANA_VERIFICATION_GUIDE.md\n\n"
            "The 80 Billion AI agent economy starts now. 🛡️⚡"
        )
    ]

    last_id = None
    for idx, t in enumerate(tweets, 1):
        print(f"\n[Step {idx}/4] Posting Tweet {idx}...")
        res = post_tweet(t, reply_to_id=last_id)
        if not res.get("success"):
            print(f"❌ Tweet {idx} failed. Error: {res.get('error')}")
            break
        last_id = res.get("tweet_id")
        time.sleep(3)

    if last_id:
        print("\n🎉 [ALL 4 TWEETS PUBLISHED SUCCESSFULLY TO X!]")


if __name__ == "__main__":
    publish_solana_thread()
