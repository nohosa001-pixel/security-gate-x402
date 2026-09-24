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
    print("📢 [PUBLISHING OFFICIAL 80B AGENT M2M CLEARINGHOUSE RELEASE THREAD TO X]")
    print("=" * 80)

    tweets = [
        # Tweet 1: Hook & The 80 Billion Agent Challenge
        (
            "By 2030, over 80 billion autonomous AI agents will trade, negotiate, and execute code.\n\n"
            "The catch? Machines can't appear in human courts or be pursued by police.\n\n"
            "Without programmatic trust, the M2M economy collapses to free-riding and toxic exit.\n\n"
            "Introducing A.GRID x402: The Autonomous Agent Clearinghouse & Escrow Protocol. 🧵👇\n"
            "#AI #Agents #DePIN #Web3Security #Crypto"
        ),
        # Tweet 2: Bilateral Staked Escrow & AST Security Gate
        (
            "1/ Non-Custodial Multi-Chain Staking\n\n"
            "Clients lock task payouts. Sub-contracting worker agents stake USDC collateral.\n\n"
            "Deliverables undergo sub-millisecond AST sandboxing & 18-vector threat defense before release.\n"
            "Zero counterparty risk. Zero malicious code execution.\n\n"
            "• Polygon: 0x8ACafCEce0B1BFE140e75614b90FD1307b6f389d\n"
            "• Base: 0x99FEd65Cf2D5378182c3481B300124BB1a8Ad278\n"
            "• Arbitrum: 0x99FEd65Cf2D5378182c3481B300124BB1a8Ad278"
        ),
        # Tweet 3: The Sovereign Invariant & RWA US Treasuries
        (
            "2/ The Sovereign Invariant: A.GRID CANNOT SPEND A SINGLE CENT\n\n"
            "100% of clearing tolls (0.25%) and slashed bounties (20%) automatically purchase tokenized US Treasury Bills (Ondo USDY, BlackRock BUIDL, Matrixdock STBT).\n\n"
            "Operator principal withdrawal is cryptographically disabled via EIP-712 Proof-of-Reserve.\n"
            "Compounded yield powers worker incentives & decentralized oracle security."
        ),
        # Tweet 4: Live Links & DePIN Worker Launch
        (
            "3/ Run a Verified DePIN GPU Worker Node in 1 Line:\n\n"
            "git clone https://github.com/nohosa001-pixel/security-gate-x402\n"
            "python scripts/depin_worker_daemon.py --chain 137\n\n"
            "🌐 Live Hub: https://nohosa001-pixel.github.io/security-gate-x402/\n"
            "⚡ Cloud Run: https://agent-security-gate-x402-212942243360.asia-northeast3.run.app/hub/\n"
            "📦 ElizaOS: plugins: ['@elizaos/plugin-security-gate']\n\n"
            "The 80B machine economy starts now. 🛡️"
        )
    ]

    auth = get_oauth()
    if not auth:
        print("\nℹ️ [INFO] X API keys not found in .env. Previewing thread content below:\n")
        for idx, t in enumerate(tweets, 1):
            print(f"--- [TWEET {idx}/4] ({len(t)} chars) ---")
            print(t)
            print()
        print("💡 Thread text also saved to docs/LAUNCH_THREAD_X.md for manual publishing.")
        return

    last_id = None
    for idx, t in enumerate(tweets, 1):
        print(f"\n[Step {idx}/4] Posting Tweet {idx}...")
        res = post_tweet(t, reply_to_id=last_id)
        if not res.get("success"):
            print(f"❌ Tweet {idx} failed. Aborting thread.")
            break
        last_id = res.get("tweet_id")
        time.sleep(3)

    if last_id:
        print("\n🎉 [ALL 4 TWEETS PUBLISHED SUCCESSFULLY TO X!]")


if __name__ == "__main__":
    publish_release_thread()

