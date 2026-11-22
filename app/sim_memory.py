"""
Self-Improvement Memory (SIM) for Continual Recursive Self-Improvement (CRSI).
Implements the structured problem-centered improvement memory schema from
Google Cloud AI & Google DeepMind (arXiv:2611.18856v1, Appendix D.3).
"""

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, List, Optional


class SelfImprovementMemory:
    """
    Records recurring harness/domain root-cause hypotheses, rationale behind edits,
    predicted vs. observed outcomes, and model/domain provenance across model upgrades.
    """

    def __init__(
        self,
        storage_path: Path,
        domain: str,
        seed_model: str = "gemini-3.8-flash",
    ):
        self.storage_path = storage_path
        self.domain = domain
        self.seed_model = seed_model
        self.data = self._load_or_init()

    def _load_or_init(self) -> Dict[str, Any]:
        if self.storage_path.exists():
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass

        init_data: Dict[str, Any] = {
            "schema": "CRSI-SIM/1.0 (arXiv:2611.18856v1)",
            "next_id": 1,
            "carried_from": {
                "domain": self.domain,
                "seed_model": self.seed_model,
            },
            "aliases": {},
            "problems": [],
        }
        self._save(init_data)
        return init_data

    def _save(self, payload: Dict[str, Any]) -> None:
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

    def record_attempt(
        self,
        root_cause: str,
        round_num: int,
        what: str,
        files: str,
        predicted: List[str],
        fixed: List[str],
        missed: List[str],
        passed: int,
        total: int,
        accepted: bool = True,
        model_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Append an attempt under an existing matching root_cause or open a new problem entry."""
        norm_cause = root_cause.strip()
        target_entry = None
        for p in self.data["problems"]:
            if p["name"].strip().lower() == norm_cause.lower():
                target_entry = p
                break

        if target_entry is None:
            pid = f"P{self.data['next_id']}"
            self.data["next_id"] += 1
            target_entry = {
                "id": pid,
                "name": norm_cause,
                "opened_round": round_num,
                "attempts": [],
            }
            self.data["problems"].append(target_entry)

        attempt = {
            "round": round_num,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "accepted": accepted,
            "what": what,
            "files": files,
            "predicted": predicted,
            "fixed": fixed,
            "missed": missed,
            "passed": passed,
            "total": total,
            "domain": self.domain,
            "model": model_name or self.seed_model,
        }
        target_entry["attempts"].append(attempt)
        # Keep recent 20 attempts per problem to bound memory size
        if len(target_entry["attempts"]) > 20:
            target_entry["attempts"] = target_entry["attempts"][-20:]

        self._save(self.data)
        return target_entry

    def get_summary(self) -> Dict[str, Any]:
        total_attempts = sum(len(p["attempts"]) for p in self.data["problems"])
        return {
            "schema": self.data.get("schema"),
            "domain": self.domain,
            "problem_entries_count": len(self.data["problems"]),
            "total_recorded_attempts": total_attempts,
            "problems_preview": [
                {
                    "id": p["id"],
                    "name": p["name"],
                    "opened_round": p["opened_round"],
                    "attempts_count": len(p["attempts"]),
                    "latest_model": p["attempts"][-1].get("model") if p["attempts"] else None,
                    "latest_pass_rate": (
                        f"{p['attempts'][-1]['passed']}/{p['attempts'][-1]['total']}"
                        if p["attempts"]
                        else "0/0"
                    ),
                }
                for p in self.data["problems"][:10]
            ],
        }
