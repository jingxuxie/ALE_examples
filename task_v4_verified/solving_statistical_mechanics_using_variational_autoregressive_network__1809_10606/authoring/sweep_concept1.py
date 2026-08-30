import os

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import importlib.util
import json
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("evaluator1", ROOT / "concept_1" / "evaluator" / "evaluate.py")
EVALUATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(EVALUATOR)


def challenge(family, seed, strength):
    rng = np.random.default_rng(seed)
    count = 20
    if family == "glass":
        couplings = np.tril(rng.normal(size=(count, count)) / np.sqrt(count), -1)
        couplings += couplings.T
    elif family == "retrieval":
        patterns = rng.choice([-1., 1.], (5, count))
        couplings = patterns.T @ patterns / count
        np.fill_diagonal(couplings, 0)
    elif family == "anisotropic":
        couplings = np.zeros((count, count))
        for row in range(4):
            for column in range(5):
                site = row * 5 + column
                for axis, neighbor in enumerate((((row + 1) % 4) * 5 + column, row * 5 + (column + 1) % 5)):
                    coupling = rng.choice([-1., 1.]) * (1.4 if axis == 0 else 0.6)
                    couplings[site, neighbor] = couplings[neighbor, site] = coupling
    else:
        couplings = np.tril(rng.normal(size=(count, count)) / np.sqrt(count), -1)
        couplings += couplings.T
        pattern = rng.choice([-1., 1.], count)
        couplings += 1.1 * np.outer(pattern, pattern) / count
        np.fill_diagonal(couplings, 0)
    couplings *= strength
    fields = rng.normal(0, 0.07, count)
    return {"n": count, "couplings": couplings.tolist(), "fields": fields.tolist()}


def worker(submission, case):
    result = {key: case[key] for key in ("id", "family", "strength", "seed")}
    try:
        model, seconds = EVALUATOR.run_case(Path(submission), case["instance"], "sweep_" + case["id"])
        result.update(EVALUATOR.exact_score(case["instance"], model), valid=True, wall_seconds=seconds)
        result["failure_cluster"] = "undercovered_probability_tails" if result["ess"] < 0.25 else "free_energy_compression_gap" if result["kl"] > 0.12 else "no_absolute_failure"
    except Exception as error:
        result.update(valid=False, reason=type(error).__name__ + ":" + str(error), failure_cluster="resource_or_artifact")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission", required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--limit", type=int, default=32)
    arguments = parser.parse_args()
    submission = EVALUATOR.validate_submission(arguments.submission)
    cases = []
    for family_index, family in enumerate(("glass", "retrieval", "anisotropic", "ferro_glass")):
        for index, strength in enumerate((0.7, 1.0, 1.3, 1.7, 2.1, 2.6, 3.2, 4.0)):
            seed = 732198 + family_index * 81 + index * 111
            cases.append({"id": family + "_" + str(index), "family": family, "strength": strength, "seed": seed,
                          "instance": challenge(family, seed, strength)})
    cases = cases[:arguments.limit]
    directory = ROOT / "concept_1" / "adversary" / arguments.label
    directory.mkdir(parents=True, exist_ok=False)
    (directory / "challenge_space.json").write_text(json.dumps(cases))
    results = []
    with ProcessPoolExecutor(max_workers=arguments.workers) as executor:
        pending = [executor.submit(worker, str(submission), case) for case in cases]
        for future in as_completed(pending):
            result = future.result()
            results.append(result)
            (directory / "results.json").write_text(json.dumps(results, indent=2))
            print(json.dumps(result), flush=True)
    summary = {"count": len(results), "clusters": {name: sum(result["failure_cluster"] == name for result in results)
               for name in sorted({result["failure_cluster"] for result in results})}, "submission": str(submission),
               "best_ess": max((result["ess"] for result in results if result["valid"]), default=None),
               "worst_ess": min((result["ess"] for result in results if result["valid"]), default=None)}
    (directory / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()
