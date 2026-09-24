"""
Official X (Twitter) Publisher for A.GRID / Security Gate x402
Publishes the core-approved standalone release announcement thread.
"""

import os
import sys
import time
import requests
from requests_oauthlib import OAuth1
from dotenv import load_dotenv

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv()

X_API_KEY = os.getenv("X_API_KEY")
X_API_SECRET = os.getenv("X_API_SECRET")
X_ACCESS_TOKEN = os.getenv("X_ACCESS_TOKEN")
X_ACCESS_TOKEN_SECRET = os.getenv("X_ACCESS_TOKEN_SECRET")

TWEETS_URL = "https://api.twitter.com/2/tweets"


def get_oauth():
    if not all([X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET]):
        return None
    return OAuth1(X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET)


def post_tweet(text: str, reply_to_id: str = None) -> dict:
    auth = get_oauth()
    if not auth:
        print("❌ [ERROR] Missing Twitter API credentials in .env")
        return {"success": False, "error": "Missing credentials"}

    payload = {"text": text}
    if reply_to_id:
        payload["reply"] = {"in_reply_to_tweet_id": reply_to_id}

    headers = {"Content-Type": "application/json"}
    try:
        resp = requests.post(TWEETS_URL, auth=auth, json=payload, headers=headers, timeout=15)
        if resp.status_code in [200, 201]:
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


def publish_release_thread():
    print("=" * 80)
    print("📢 [PUBLISHING OFFICIAL RELEASE THREAD TO X]")
    print("=" * 80)

    tweet_1_text = (
        "Autonomous AI agents now manage real capital. Yet 99% remain defenseless against prompt injection and fund drains.\n\n"
        "Audited & APPROVED by @elizaos core maintainers (PR #31451), @elizaos/plugin-security-gate is officially live!\n\n"
        "Deterministic, fail-closed safety in 1 line:\n"
        'plugins: ["@elizaos/plugin-security-gate"]\n\n'
        "Audited PR: https://github.com/elizaos/eliza/pull/31451\n"
        "#AI #Agent #ElizaOS #CryptoSecurity"
    )

    print("\n[Step 1/2] Posting Tweet 1...")
    res_1 = post_tweet(tweet_1_text)

    if not res_1.get("success"):
        print("\n❌ Tweet 1 failed. Aborting thread.")
        return

    tweet_1_id = res_1.get("tweet_id")
    print("⏳ Waiting 3 seconds before replying with Tweet 2...")
    time.sleep(3)

    tweet_2_text = (
        "Live & 100% verified across 3 EVM mainnets:\n"
        "• Polygon (137): 0x5cC5Afa2a97599d492A3E408Fdd95fD0b520f173\n"
        "• Base (8453): 0x306e69E59E5bCEa769C6CeA76A79AFA8f2A5F408\n"
        "• Arbitrum One (42161): 0x306e69E59E5bCEa769C6CeA76A79AFA8f2A5F408\n\n"
        "Non-custodial EIP-712 attestations, agent credit scoring, & uncollateralized lending.\n"
        "Built for the autonomous machine economy. 🛡️"
    )

    print("\n[Step 2/2] Posting Tweet 2 (Thread Reply)...")
    res_2 = post_tweet(tweet_2_text, reply_to_id=tweet_1_id)

    if res_2.get("success"):
        print("\n🎉 [ALL TWEETS PUBLISHED SUCCESSFULLY!]")
    else:
        print("\n⚠️ Tweet 2 reply failed, but Tweet 1 is live.")


if __name__ == "__main__":
    publish_release_thread()
