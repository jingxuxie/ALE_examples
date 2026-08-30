import os

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"

import argparse
import json
from pathlib import Path
import numpy as np
from sweep_concept1 import EVALUATOR, ROOT, worker


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission", required=True)
    parser.add_argument("--label", required=True)
    arguments = parser.parse_args()
    submission = EVALUATOR.validate_submission(arguments.submission)
    directory = ROOT / "concept_1" / "adversary" / arguments.label
    directory.mkdir(parents=True, exist_ok=False)
    cases, results = [], []
    for index, strength in enumerate((0.8, 1.3, 2.0, 3.0)):
        for variant, partition in enumerate(([4, 4, 4, 4, 4], [5, 5, 5, 5], [6, 7, 7])):
            rng = np.random.default_rng(175721 + index * 177 + variant)
            couplings = np.zeros((20, 20))
            fields = np.zeros(20)
            start = 0
            for size in partition:
                block = np.full((size, size), -strength)
                np.fill_diagonal(block, 0)
                couplings[start:start + size, start:start + size] = block
                fields[start:start + size] = strength * (1.0 if size % 2 == 0 else 2.0) + rng.normal(0, 0.015, size)
                start += size
            perturbation = np.tril(rng.normal(0, 0.004, (20, 20)), -1)
            couplings += perturbation + perturbation.T
            order = rng.permutation(20)
            gauge = rng.choice([-1., 1.], 20)
            couplings = couplings[np.ix_(order, order)] * gauge[:, None] * gauge[None, :]
            fields = fields[order] * gauge
            case = {"id": "modular_" + str(index) + "_" + str(variant), "family": "competing_local_sectors",
                    "strength": strength, "seed": 175721 + index * 177 + variant,
                    "partition": partition, "instance": {"n": 20, "couplings": couplings.tolist(), "fields": fields.tolist()}}
            cases.append(case)
            result = worker(str(submission), case)
            results.append(result)
            (directory / "results.json").write_text(json.dumps(results, indent=2))
            (directory / "challenge_space.json").write_text(json.dumps(cases))
            print(json.dumps(result), flush=True)
    (directory / "summary.json").write_text(json.dumps({"count": len(results),
        "scientific_motivation": "Competing local magnetization sectors in antiferromagnetic clusters induce nonlinear prefix conditionals; weak inter-cluster couplings retain a connected dense Ising model.",
        "absolute_failures": sum(result.get("kl", 1) > 0.12 or result.get("ess", 0) < 0.25 for result in results)}, indent=2))


if __name__ == "__main__":
    main()
