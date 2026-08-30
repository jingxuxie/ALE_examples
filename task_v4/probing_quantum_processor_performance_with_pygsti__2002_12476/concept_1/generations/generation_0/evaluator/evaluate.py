import argparse
import json
import time
from pathlib import Path

import numpy as np


def evaluate(submission):
    started = time.monotonic()
    root = Path(__file__).resolve().parent
    result = {"core_score": 0., "worst_family_score": 0., "runtime_seconds": 0.,
              "resource_score": 0., "passed": False, "valid": False, "reason": ""}
    try:
        path = Path(submission)
        if path.is_dir():
            path = path / "design.json"
        if path.stat().st_size > 100000:
            raise ValueError("submission exceeds 100 KB")
        value = json.loads(path.read_text())
        if not isinstance(value, dict) or set(value) != {"batches"}:
            raise ValueError("expected exactly the batches field")
        data = np.load(root / "hidden/benchmark.npz", allow_pickle=False)
        contract = json.loads((root / "hidden/contract.json").read_text())
        batches = value["batches"]
        if not isinstance(batches, list) or len(batches) != len(data["costs"]):
            raise ValueError("wrong batch-vector length")
        if any(type(entry) is not int or not 0 <= entry <= contract["max_batches_per_circuit"] for entry in batches):
            raise ValueError("batch counts must be bounded nonnegative integers")
        counts = np.array(batches, dtype=np.int64)
        active = int(np.count_nonzero(counts))
        cost = int(counts @ data["costs"] + active * contract["setup_ticks"])
        if not 1 <= active <= contract["max_distinct_circuits"]:
            raise ValueError("distinct-circuit limit violated")
        if cost > contract["execution_budget_ticks"]:
            raise ValueError("execution budget exceeded")
        candidate_risks = []
        for features in data["features"]:
            information = (features.T * (counts * contract["shots_per_batch"])) @ features
            information += np.eye(14) * 1e-10
            eigenvalues = np.linalg.eigvalsh(information)
            if eigenvalues[0] <= 0:
                raise ValueError("numerically nonpositive information")
            covariance = np.linalg.solve(information, np.eye(14))
            candidate_risks.append(float(np.trace(covariance[:12, :12])))
        candidate_risks = np.array(candidate_risks)
        if not np.all(np.isfinite(candidate_risks)) or np.any(candidate_risks <= 0):
            raise ValueError("invalid information risk")
        family_scores = {}
        family_risks = {}
        for family in np.unique(data["families"]):
            mask = data["families"] == family
            family_scores[str(family)] = float(1 - candidate_risks[mask].mean() / data["baseline_risks"][mask].mean())
            family_risks[str(family)] = float(candidate_risks[mask].mean())
        result.update(valid=True,
                      core_score=float(1 - candidate_risks.mean() / data["baseline_risks"].mean()),
                      worst_family_score=min(family_scores.values()), family_scores=family_scores,
                      mean_risk=float(candidate_risks.mean()), family_risks=family_risks,
                      execution_ticks=cost, distinct_circuits=active,
                      resource_score=float(1 - cost / contract["execution_budget_ticks"]))
        result["passed"] = (result["core_score"] >= contract["target_core_reduction"] and
                            result["worst_family_score"] >= contract["target_worst_family_reduction"])
        result["reason"] = "all frozen targets met" if result["passed"] else "insufficient robust risk reduction"
    except (OSError, ValueError, TypeError, KeyError, OverflowError, np.linalg.LinAlgError) as error:
        result["reason"] = str(error)
    result["runtime_seconds"] = time.monotonic() - started
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission", required=True)
    parser.add_argument("--output")
    args = parser.parse_args()
    result = evaluate(args.submission)
    encoded = json.dumps(result, indent=2, allow_nan=False) + "\n"
    if args.output:
        Path(args.output).write_text(encoded)
    print(encoded, end="")


if __name__ == "__main__":
    main()
