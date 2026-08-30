import json
import math
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
CONCEPT = ROOT / "concept_1"
PRIVATE = CONCEPT / "adversary/broad_native"
report = json.loads((PRIVATE / "candidate_report.json").read_text())
if not report["complete"] or not all(case["valid"] for case in report["cases"]):
    raise ValueError("cannot mark incomplete or invalid audit as successful")
families = {}
discordant = 0
for case in report["cases"]:
    totals = families.setdefault(case["family"], {"stock_errors": 0, "champion_errors": 0, "shots": 0})
    totals["stock_errors"] += case["baseline_errors"]
    totals["champion_errors"] += case["errors"]
    totals["shots"] += case["shots"]
    truth = np.load(PRIVATE / "labels" / (case["id"] + ".npy"), allow_pickle=False)
    baseline = np.load(PRIVATE / "stock_baseline" / (case["id"] + ".npy"), allow_pickle=False)
    candidate = np.load(PRIVATE / "candidate_predictions" / (case["id"] + ".npy"), allow_pickle=False)
    discordant += int(np.count_nonzero((baseline != truth) != (candidate != truth)))
ratios = {family: totals["champion_errors"] / totals["stock_errors"] for family, totals in families.items()}
delta = sum(totals["stock_errors"] - totals["champion_errors"] for totals in families.values())
shots = sum(totals["shots"] for totals in families.values())
sigma = delta / math.sqrt(max(1, discordant - delta**2 / shots))
core = sum(ratios.values()) / len(ratios)
worst = max(ratios.values())
passed = core <= 0.8 and worst <= 0.95 and sigma >= 3
summary = {"family_failure_ratios": ratios, "family_totals": families,
           "core_failure_ratio": core, "worst_family_ratio": worst, "paired_sigma": sigma,
           "shots": shots, "max_request_seconds": max(case["seconds"] for case in report["cases"]),
           "original_quality_and_resource_target_met": passed,
           "decision": "No fixed-target violation found in this broader grid; do not invent a failure by arbitrarily tightening the threshold." if passed else "Further ratchet required"}
(PRIVATE / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
status = json.loads((CONCEPT / "status.json").read_text())
fresh = json.loads((CONCEPT / "attempts/v_1_score.json").read_text())
status.update({"status": "solved" if passed else "pending_ratchet", "fresh_agent_score": fresh,
               "champion": "champions/generation_1", "champion_search": summary,
               "solvability": "Demonstrated by the fresh executable submission under the declared resource limits.",
               "substantive_capability_failure": None})
(CONCEPT / "status.json").write_text(json.dumps(status, indent=2) + "\n")
print(json.dumps(summary, indent=2))
