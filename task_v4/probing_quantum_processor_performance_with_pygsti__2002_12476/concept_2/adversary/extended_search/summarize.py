import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone

import portfolio as search


def main():
    freeze = json.loads((search.ROOT / "adversary/freeze.json").read_text())
    integrity = {name: hashlib.sha256((search.ROOT / name).read_bytes()).hexdigest() == expected
                 for name, expected in freeze["file_sha256"].items()}
    if not all(integrity.values()):
        raise RuntimeError("frozen assets changed; do not claim a validated frozen-target result")
    paths = sorted(path for path in search.OUTPUT.glob("*_best_witness.json")
                   if path.name != "validated_best_witness.json")
    paths.append(search.OUTPUT / "best_witness.json")
    candidates = []
    for path in paths:
        result = search.EVALUATOR.evaluate(path)
        if result["valid"] and search.feasible(result):
            candidates.append((result["worst_family_score"], path, result))
    score, path, result = max(candidates)
    witness = json.loads(path.read_text())
    search.save("validated_best_witness.json", witness)
    command = [sys.executable, "-B", str(search.ROOT / "evaluator/evaluate.py"),
               "--submission", str(search.OUTPUT / "validated_best_witness.json"),
               "--output", str(search.OUTPUT / "validated_best_evaluation.json")]
    subprocess.run(command, check=True, capture_output=True, text=True)
    independent = json.loads((search.OUTPUT / "validated_best_evaluation.json").read_text())
    records = []
    checkpoint_recovered = []
    for worker in range(4):
        path = search.OUTPUT / ("worker_" + str(worker) + "_final.json")
        if path.exists():
            records.append(json.loads(path.read_text())["counts"])
        else:
            path = search.OUTPUT / ("worker_" + str(worker) + "_history.json")
            records.append(json.loads(path.read_text())[-1]["counts"])
            checkpoint_recovered.append(worker)
    for name in ["structured_summary.json", "reorder_summary.json", "global_summary.json"]:
        records.append(json.loads((search.OUTPUT / name).read_text())["counts"])
    names = set().union(*(record.keys() for record in records))
    counts = {name: sum(record.get(name, 0) for record in records) for name in sorted(names)}
    counts["total_independent_evaluator_calls_lower_bound"] = counts["independent_evaluator_calls"] + 4 + len(paths) + 1
    structured = json.loads((search.OUTPUT / "structured_summary.json").read_text())
    run = json.loads((search.OUTPUT / "run_manifest.json").read_text())
    now = datetime.now(timezone.utc)
    seconds = (now - datetime.fromisoformat(run["started_at_utc"])).total_seconds()
    scenarios = independent["scenarios"]
    report = {"completed_at_utc": now.isoformat(), "elapsed_seconds_since_portfolio_launch": seconds,
              "target": .065, "core_score": independent["core_score"],
              "worst_family_score": independent["worst_family_score"],
              "passed": independent["passed"], "valid": independent["valid"],
              "calibration_accepted": independent["calibration_accepted"], "margins": search.margins(independent),
              "maximum_calibration_error": max(family["max_abs_error"] for scenario in scenarios for family in scenario["calibration"].values()),
              "maximum_family_rms_error": max(family["rms_error"] for scenario in scenarios for family in scenario["calibration"].values()),
              "maximum_final_leakage": max(scenario["final_leakage"] for scenario in scenarios),
              "counts": counts, "distinct_structured_circuit_candidates": structured["unique_structured_candidates"],
              "counter_definition": "Each circuit_scenario_evaluation propagates one circuit in one tolerance scenario through both physical and reported models. Continuous finite-difference and discrete-population calls are counted. These are simulator evaluations, not independent witnesses.",
              "evaluation_counts_are_lower_bounds": True,
              "checkpoint_recovered_workers": checkpoint_recovered,
              "counter_completeness": "Two workers reached the hard wall-time cutoff during discrete search; their last durable checkpoint counters are included, but subsequent unfinished work is not. Auxiliary searches have complete counters. Some repeated final-audit reproductions are also omitted, so the reported totals are conservative lower bounds.",
              "exact_evaluator_cli_validated": True, "evaluator_runtime_seconds": independent["runtime_seconds"],
              "frozen_asset_hashes_unchanged": all(integrity.values()), "asset_integrity": integrity,
              "fresh_attempt_outputs_inspected": False, "participant_evaluator_status_edited": False,
              "solvability": "demonstrated" if independent["passed"] else "unknown",
              "interpretation": "A passing witness was found." if independent["passed"] else "No passing witness found in the bounded search; this is not an impossibility result.",
              "witness": "adversary/extended_search/validated_best_witness.json",
              "evaluation": "adversary/extended_search/validated_best_evaluation.json"}
    search.save("final_report.json", report)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
