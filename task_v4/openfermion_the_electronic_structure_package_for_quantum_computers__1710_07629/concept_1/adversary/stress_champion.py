import argparse
import json
import os
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evaluator"))
from evaluate import validate_solution


def perturbation_probe(case, solution, seed):
    generator = np.random.default_rng(seed)
    orbital = np.asarray(solution["orbital"])
    auxiliary = np.asarray(solution["auxiliary"])
    original = validate_solution(case, solution)
    best = original
    for scale in (0.002, 0.01, 0.05):
        for trial in range(12):
            candidates = []
            for matrix in (orbital, auxiliary):
                noise = generator.normal(size=matrix.shape)
                skew = noise - noise.T
                skew *= scale / np.linalg.norm(skew)
                rotation = np.linalg.solve(np.eye(len(matrix)) - skew, np.eye(len(matrix)) + skew)
                candidates.append(matrix @ rotation)
            candidate = {"orbital": candidates[0], "auxiliary": candidates[1]}
            best = min(best, validate_solution(case, candidate))
    return max(0.0, 1 - best / original)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("submission", type=Path)
    parser.add_argument("--generation", type=int, default=1)
    parser.add_argument("--supported-only", action="store_true")
    arguments = parser.parse_args()
    submission = arguments.submission.resolve(strict=True)
    pool = ROOT / "adversary/broad_search"
    suffix = "_supported" if arguments.supported_only else ""
    destination = ROOT / "adversary" / f"champion_{arguments.generation}_stress{suffix}"
    destination.mkdir(exist_ok=True)
    request = json.loads((pool / "cases.json").read_text())
    original_pool_count = len(request["cases"])
    if arguments.supported_only:
        request["cases"] = [case for case in request["cases"] if len(case["one_body"]) <= 16]
    private_solutions = json.loads((pool / "privileged_multistart_solution.json").read_text())
    private_solutions = {item["id"]: item for item in private_solutions["solutions"]}
    cases = {case["id"]: case for case in request["cases"]}
    records, failures = [], []
    for batch in range((len(request["cases"]) + 17) // 18):
        selection = request["cases"][18 * batch:18 * (batch + 1)]
        request_path = destination / f"batch_{batch}.json"
        request_path.write_text(json.dumps({"cases": selection, "seconds_per_case": 10}, allow_nan=False))
        report_path = destination / f"batch_{batch}.report.json"
        response_path = destination / f"batch_{batch}.response.json"
        if not report_path.exists():
            command = ["/usr/bin/python3", str(ROOT.parent / "private/affinity.py"), str(ROOT / "adversary/capture_evaluate.py"), str(submission), "--cases", str(request_path), "--report", str(report_path), "--response", str(response_path)]
            with (destination / f"batch_{batch}.log").open("wb") as log:
                subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, env=dict(os.environ, OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1"), timeout=220)
        report = json.loads(report_path.read_text())
        if not report.get("valid"):
            failures.append({"batch": batch, "reason": report["reason"], "scientific_quality_counterexample": False})
            continue
        submitted_solutions = json.loads(response_path.read_text())
        submitted_solutions = {item["id"]: item for item in submitted_solutions["solutions"]}
        for measured in report["cases"]:
            case = cases[measured["id"]]
            private_cost = validate_solution(case, private_solutions[case["id"]])
            gap = 1 - private_cost / measured["cost"]
            record = dict(measured, private_cost=private_cost, attainable_extra_reduction=gap, dimension=len(case["one_body"]), within_original_dimension_range=len(case["one_body"]) <= 16)
            if gap >= 0.08:
                record["best_small_perturbation_reduction"] = perturbation_probe(case, submitted_solutions[case["id"]], 901 + len(records))
                record["root_cause_evidence"] = "lower-cost coordinated gauge exists, but sampled local perturbations do not improve" if record["best_small_perturbation_reduction"] < 1e-4 else "unfinished local optimization: small perturbations improve cost"
            records.append(record)
        print(json.dumps({"batch": batch, "valid": True, "runtime": report["runtime_seconds"], "cases_scored": len(records)}), flush=True)
    clusters = defaultdict(list)
    for record in records:
        if record["attainable_extra_reduction"] >= 0.08:
            scope = "original_range" if record["within_original_dimension_range"] else "larger_disclosed_extension_required"
            clusters[(record["family"], scope)].append(record["id"])
    result = {"submitted_champion": str(submission), "requested_cases": len(request["cases"]), "original_pool_count": original_pool_count, "out_of_contract_excluded": original_pool_count - len(request["cases"]), "valid_cases": len(records), "failures": failures, "at_least_8_percent_quality_gaps": sum(record["attainable_extra_reduction"] >= 0.08 for record in records), "at_least_10_percent_quality_gaps": sum(record["attainable_extra_reduction"] >= 0.10 for record in records), "strata_for_root_cause_investigation": [{"family": key[0], "scope": key[1], "ids": identifiers} for key, identifiers in clusters.items()], "records": records, "generation_rule": "Original tests remain unchanged. Out-of-contract memory failures do not count as scientific hardness. Extra-reduction artifacts demonstrate quality feasibility, not an unprivileged runtime-valid general solver."}
    (destination / "report.json").write_text(json.dumps(result, indent=2))
    print(json.dumps({key: value for key, value in result.items() if key != "records"}, indent=2))


if __name__ == "__main__":
    main()
