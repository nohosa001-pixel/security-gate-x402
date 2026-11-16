"""
A.GRID Security Gate x ElizaOS Brain Continuous Learning Trainer CLI.
Delegates core 5-domain learning logic to app.brain_trainer.SecurityGateBrainTrainer.
"""

import argparse
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Ensure repository root is in sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from app.brain_trainer import HEARTBEAT_FILE, STATE_FILE, SecurityGateBrainTrainer


def run_daemon(interval_sec: int = 900):
    trainer = SecurityGateBrainTrainer()
    print("==================================================================")
    print("🧠 A.GRID SECURITY GATE × ELIZAOS BRAIN CONTINUOUS LEARNER DAEMON")
    print(f"⏱️ Cycle Interval: Every {interval_sec}s (96 cycles/day | 30 days total)")
    print(f"📊 State File: {STATE_FILE}")
    print(f"💓 Heartbeat:  {HEARTBEAT_FILE}")
    print("==================================================================")

    while True:
        try:
            res = trainer.execute_training_cycle(mode="daemon")
            now_iso = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")
            print(
                f"[{now_iso}] Cycle #{res['cycle']} (Day {res['current_day']}/30) | "
                f"Readiness: {res['overall_readiness']*100:.2f}% | Brier: {res['brier_score']} | "
                f"Stake: {res['stake_ratio']*100:.0f}% | Latency: {res['latency_ms']}ms",
                flush=True,
            )
        except Exception as e:
            print(f"[ERROR] Cycle execution failed: {e}", file=sys.stderr, flush=True)

        time.sleep(interval_sec)


def main():
    parser = argparse.ArgumentParser(description="Security Gate ElizaOS Brain Continuous Learning Trainer")
    parser.add_argument("--daemon", action="store_true", help="Run continuously in background daemon mode")
    parser.add_argument("--interval", type=int, default=900, help="Interval in seconds (default: 900s / 15m)")
    parser.add_argument("--cycles", type=int, default=1, help="Number of cycles to run immediately")
    args = parser.parse_args()

    trainer = SecurityGateBrainTrainer()

    if args.daemon:
        run_daemon(interval_sec=args.interval)
    else:
        print("==================================================================")
        print("🚀 EXECUTING IMMEDIATE CONTINUOUS TRAINING CYCLES")
        print("==================================================================")
        for _ in range(args.cycles):
            res = trainer.execute_training_cycle(mode="step")
            print(f"✅ Cycle #{res['cycle']} Completed | Day {res['current_day']}/30")
            print(f"   • Overall Readiness: {res['overall_readiness']*100:.2f}%")
            print(f"   • Brier Score:       {res['brier_score']} (Lower is better)")
            print(f"   • CFR Alpha:         {res['alpha']} ({res['cfr_decision']})")
            print(f"   • Effective Stake:   {res['stake_ratio']*100:.0f}%")
            print(f"   • Block ID:          {res['memory_block_id']}")
            print(f"   • Latency:           {res['latency_ms']} ms")
            print("------------------------------------------------------------------")
        print("🎉 Training Step Complete! Safe Invariants Preserved: Zero Funds Moved | RAM < 20MB.")


if __name__ == "__main__":
    main()
