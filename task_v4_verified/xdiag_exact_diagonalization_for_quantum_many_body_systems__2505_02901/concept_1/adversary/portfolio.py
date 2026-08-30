import argparse
import json
import os
import sys
import time
from pathlib import Path

os.environ["OPENBLAS_NUM_THREADS"] = "1"

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "participant" / "baseline"))
sys.path.insert(0, str(ROOT / "evaluator"))
from evaluate import load_configurations
from fleet import load_fleet, objective
from scoring import exact_score, strict_json
from solve import solve
from build_data import write_json


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--trials", type=int, default=256)
    arguments = parser.parse_args()
    suite = strict_json((ROOT / "evaluator" / "hidden" / "suite.json").read_text())
    baseline = strict_json((ROOT / "evaluator" / "hidden" / "baseline.json").read_text())
    report = {"kind": "offline_quality_certificates_not_online_solver", "fleets": {}}
    families = {}
    for entry in suite["fleets"]:
        directory = ROOT / "evaluator" / "hidden" / entry["directory"]
        manifest, cases = load_fleet(directory)
        started = time.monotonic()
        policy = solve(manifest, cases, trials=arguments.trials, seed=7714, diversify=True)
        previous = strict_json((ROOT / "champions" / "baseline" / (entry["id"] + ".json")).read_text())
        if objective(cases, previous["cases"]) < objective(cases, policy["cases"]):
            policy = previous
        seconds = time.monotonic() - started
        manifest, configurations = load_configurations(directory)
        result = exact_score(manifest, configurations, policy)
        improvement = 100 * (1 - result["objective"] / baseline["fleets"][entry["id"]]["objective"])
        families.setdefault(entry["family"], []).append(improvement)
        report["fleets"][entry["id"]] = dict(result, search_seconds=seconds,
                                             improvement_percent=improvement, trials=arguments.trials)
        write_json(ROOT / "champions" / "offline_portfolio" / (entry["id"] + ".json"), policy)
        write_json(ROOT / "adversary" / "portfolio_report.json", report)
        print("portfolio", entry["id"], improvement, "seconds", seconds, flush=True)
    report["family_scores"] = {family: sum(values) / len(values) for family, values in families.items()}
    report["core_score"] = sum(report["family_scores"].values()) / len(families)
    report["worst_family_score"] = min(report["family_scores"].values())
    targets = strict_json((ROOT / "evaluator" / "hidden" / "targets.json").read_text())
    report["quality_target_certified"] = (report["core_score"] >= targets["core_improvement_percent"]
                                           and report["worst_family_score"] >= targets["worst_family_improvement_percent"])
    report["online_solvability_demonstrated"] = False
    write_json(ROOT / "adversary" / "portfolio_report.json", report)


if __name__ == "__main__":
    main()
