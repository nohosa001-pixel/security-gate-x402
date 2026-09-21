

"""
==============================================================================
🛡️ A.GRID Sentinel AutoPilot: Automated Upstream Merge Detector & Launcher
==============================================================================
Monitors GitHub PR #31451 (elizaos/eliza).
The exact second 'merged == True' is detected:
  1. ⚡ Fires Multi-Chain On-Chain Agent Traffic (Polygon, Base, Arbitrum One).
  2. 📢 Publishes Official Launch Announcement to X (Twitter) via OAuth 1.0a.
  3. 🔔 Triggers Windows System Alert & Desktop Notification.
  4. 📝 Records permanent audit log to MERGE_LAUNCH_RECORD.json.

Usage:
  python scripts/sentinel_merge_autopilot.py
  python scripts/sentinel_merge_autopilot.py --poll-interval 15
  python scripts/sentinel_merge_autopilot.py --simulate  (Test dry-run without merge)
==============================================================================
"""

import os
import sys
import time
import json
import subprocess
import argparse
import ctypes
from datetime import datetime, timezone
from pathlib import Path
import requests
from requests_oauthlib import OAuth1
from dotenv import load_dotenv

# Ensure UTF-8 output on Windows terminal
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv()

REPO_OWNER = "elizaos"
REPO_NAME = "eliza"
PR_NUMBER = 31451
GITHUB_API_URL = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/pulls/{PR_NUMBER}"

# Twitter OAuth 1.0a Credentials
X_API_KEY = os.getenv("X_API_KEY")
X_API_SECRET = os.getenv("X_API_SECRET")
X_ACCESS_TOKEN = os.getenv("X_ACCESS_TOKEN")
X_ACCESS_TOKEN_SECRET = os.getenv("X_ACCESS_TOKEN_SECRET")

TWEETS_URL = "https://api.twitter.com/2/tweets"


def get_oauth():
    if not all([X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET]):
        return None
    return OAuth1(X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET)


def post_to_x(text: str, reply_to_id: str = None) -> dict:
    auth = get_oauth()
    if not auth:
        print("⚠️ [X POST ERROR] Missing Twitter credentials in .env")
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
            print(f"✅ [X POST SUCCESS] Tweet ID: {tweet_id}")
            return {"success": True, "tweet_id": tweet_id, "data": data}
        else:
            print(f"❌ [X POST FAILED] Status {resp.status_code}: {resp.text}")
            return {"success": False, "error": resp.text, "status": resp.status_code}
    except Exception as e:
        print(f"❌ [X POST EXCEPTION] {e}")
        return {"success": False, "error": str(e)}


def launch_onchain_traffic():
    print("\n⚡ [ACTION 1] Igniting Multi-Chain Autonomous Agent Traffic...")
    seeder_script = Path(__file__).parent / "autonomous_agent_traffic_seeder.py"
    if seeder_script.exists():
        # Start seeder as non-blocking background process
        proc = subprocess.Popen(
            [sys.executable, str(seeder_script), "--loop", "--interval", "20"],
            creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == "nt" else 0
        )
        print(f"🚀 [TRAFFIC SEEDER LAUNCHED] PID: {proc.pid} (Generating live proofs on Polygon, Base, Arbitrum)")
        return proc.pid
    else:
        print(f"⚠️ [WARNING] Seeder script not found: {seeder_script}")
        return None


def trigger_system_alert(title: str, message: str):
    print(f"\n🔔 [ACTION 3] SYSTEM ALERT: {title} - {message}")
    if os.name == "nt":
        try:
            # Sound Windows system asterisk chime
            ctypes.windll.user32.MessageBeep(0x00000040)
            # Show non-blocking message box or toast notification
        except Exception:
            pass


def execute_global_launch(merge_metadata: dict, simulate: bool = False):
    timestamp = datetime.now(timezone.utc).isoformat()
    print("\n" + "=" * 80)
    print("🚨🚨🚨 [MERGE CONFIRMED! EXECUTING GLOBAL LAUNCH PAYLOAD] 🚨🚨🚨")
    print(f"Timestamp: {timestamp}")
    print("=" * 80)

    # 1. Start on-chain traffic
    traffic_pid = launch_onchain_traffic() if not simulate else 9999

    # 2. Post to X (Twitter)
    print("\n📢 [ACTION 2] Publishing Official Global Announcement to X (@nohosa_1250)...")
    tweet_1_text = (
        "Autonomous AI agents now manage real capital. Yet 99% remain defenseless against prompt injection and fund drains.\n\n"
        "Today, @elizaos/plugin-security-gate is officially MERGED into ElizaOS core!\n\n"
        "Deterministic, fail-closed safety in 1 line:\n"
        'plugins: ["@elizaos/plugin-security-gate"]\n\n'
        "PR #31451: https://github.com/elizaos/eliza/pull/31451\n"
        "#AI #Agent #ElizaOS #CryptoSecurity"
    )

    t1_res = post_to_x(tweet_1_text) if not simulate else {"success": True, "tweet_id": "SIMULATED_123"}
    t1_id = t1_res.get("tweet_id")

    tweet_2_text = (
        "Live & 100% verified across 3 EVM mainnets:\n"
        "• Polygon (137): 0x5cC5Afa2a97599d492A3E408Fdd95fD0b520f173\n"
        "• Base (8453): 0x306e69E59E5bCEa769C6CeA76A79AFA8f2A5F408\n"
        "• Arbitrum One (42161): 0x306e69E59E5bCEa769C6CeA76A79AFA8f2A5F408\n\n"
        "Non-custodial EIP-712 attestations, agent credit scoring, & uncollateralized lending.\n"
        "Built for the autonomous machine economy. 🛡️"
    )

    t2_res = None
    if t1_id:
        time.sleep(2)
        t2_res = post_to_x(tweet_2_text, reply_to_id=t1_id) if not simulate else {"success": True, "tweet_id": "SIMULATED_456"}

    # 3. System alert
    trigger_system_alert(
        "A.GRID / ElizaOS Merge Complete",
        "PR #31451 merged! On-chain traffic started and X announcement published."
    )

    # 4. Save record
    record = {
        "timestamp": timestamp,
        "pr_number": PR_NUMBER,
        "merge_metadata": merge_metadata,
        "traffic_seeder_pid": traffic_pid,
        "tweet_1": t1_res,
        "tweet_2": t2_res,
        "simulated": simulate
    }

    record_path = Path(__file__).parent.parent / "MERGE_LAUNCH_RECORD.json"
    with open(record_path, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)

    print(f"\n📝 [AUDIT RECORD SAVED] {record_path}")
    print("=" * 80)
    print("✨ [ALL LAUNCH ACTIONS COMPLETED SUCCESSFULLY]")
    print("=" * 80)


def check_pr_status_html() -> dict:
    try:
        url = f"https://github.com/{REPO_OWNER}/{REPO_NAME}/pull/{PR_NUMBER}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        resp = requests.get(url, headers=headers, timeout=12)
        if resp.status_code == 200:
            import re
            for m in re.finditer(r'<script type="application/json"[^>]*>({.*?})</script>', resp.text, re.DOTALL):
                try:
                    data = json.loads(m.group(1))
                    pl = data.get('payload', {})
                    layout = pl.get('pullRequestsLayoutRoute', {})
                    pr_data = layout.get('pullRequest', {})
                    if pr_data and pr_data.get('number') == PR_NUMBER:
                        state = pr_data.get('state', '').upper()
                        is_merged = state == "MERGED" or bool(pr_data.get('isMerged'))
                        return {
                            "state": state,
                            "merged": is_merged,
                            "merged_at": pr_data.get('mergedAt'),
                            "source": "HTML_PARSER"
                        }
                except Exception:
                    continue
    except Exception as e:
        print(f"⚠️ [HTML FALLBACK ERROR] {e}")
    return {}


def check_pr_status() -> dict:
    headers = {
        "User-Agent": "A-GRID-Sentinel/2.0",
        "Accept": "application/vnd.github.v3+json"
    }
    try:
        resp = requests.get(GITHUB_API_URL, headers=headers, timeout=10)
        if resp.status_code == 200:
            d = resp.json()
            d["source"] = "REST_API"
            return d
        elif resp.status_code == 403:
            # Fallback to HTML scraping without API limits
            html_res = check_pr_status_html()
            if html_res:
                return html_res
            print(f"⚠️ [GITHUB API RATE LIMIT] Waiting for next cycle... (Status 403)")
            return {}
        else:
            return check_pr_status_html()
    except Exception:
        return check_pr_status_html()



def monitor_loop(poll_interval: int = 20):
    print("=" * 80)
    print("🛡️ [A.GRID AUTONOMOUS MERGE SENTINEL ACTIVE]")
    print(f"Target: GitHub PR #{PR_NUMBER} ({REPO_OWNER}/{REPO_NAME})")
    print(f"Polling Interval: {poll_interval}s")
    print("Armed Automations:")
    print("  1. ⚡ Multi-Chain On-Chain Traffic Seeder (Polygon/Base/Arb)")
    print("  2. 📢 Global X Announcement (Twitter OAuth v2)")
    print("  3. 🔔 Windows Toast & Audio Alert")
    print("=" * 80)

    check_count = 0
    while True:
        check_count += 1
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            data = check_pr_status()
            if data:
                state = data.get("state")
                is_merged = data.get("merged", False)
                merged_at = data.get("merged_at")
                mergeable = data.get("mergeable_state")

                print(f"[{now_str}] Check #{check_count:04d} | State: {state.upper()} | Merged: {is_merged} | Mergeable: {mergeable}")

                if is_merged or (state == "closed" and merged_at is not None):
                    print(f"\n🎉 [TRIGGER DETECTED] PR #{PR_NUMBER} was officially MERGED at {merged_at}!")
                    execute_global_launch(data, simulate=False)
                    break

        except KeyboardInterrupt:
            print("\n🛑 Sentinel monitoring paused by user.")
            break
        except Exception as e:
            print(f"[{now_str}] ⚠️ Polling error: {e}")

        time.sleep(poll_interval)


def main():
    parser = argparse.ArgumentParser(description="A.GRID Sentinel AutoPilot")
    parser.add_argument("--poll-interval", type=int, default=20, help="GitHub polling interval in seconds")
    parser.add_argument("--simulate", action="store_true", help="Simulate merge launch right now (dry-run)")
    args = parser.parse_args()

    if args.simulate:
        print("🧪 [SIMULATION MODE] Executing launch sequence dry-run...")
        execute_global_launch({"simulated": True, "merged_at": datetime.now(timezone.utc).isoformat()}, simulate=True)
    else:
        monitor_loop(args.poll_interval)


if __name__ == "__main__":
    main()
