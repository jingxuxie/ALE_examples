import os

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
import numpy as np
from sweep_concept1 import EVALUATOR, ROOT, worker


def challenge(family, seed, strength, variant):
    random = np.random.default_rng(seed)
    count = 20
    couplings = np.zeros((count, count))
    fields = np.zeros(count)
    if family in ("interacting_regions", "nonuniform_regions"):
        partition = ([4, 4, 4, 4, 4], [5, 5, 5, 5], [6, 7, 7])[variant % 3]
        start = 0
        membership = np.zeros(count, dtype=int)
        for block_index, size in enumerate(partition):
            disorder = 0.03 if family == "interacting_regions" else strength
            block = np.tril(-2.5 * np.exp(random.normal(-disorder**2 / 2, disorder, (size, size))), -1)
            couplings[start:start + size, start:start + size] = block + block.T
            fields[start:start + size] = 2.5 * (1 if size % 2 == 0 else 2) + random.normal(0, 0.08, size)
            membership[start:start + size] = block_index
            start += size
        external = strength if family == "interacting_regions" else 0.08
        perturbation = np.tril(random.normal(0, external, (count, count)), -1)
        perturbation *= membership[:, None] != membership[None, :]
        couplings += perturbation + perturbation.T
    else:
        degree = (3, 4, 6)[variant % 3]
        permutation = random.permutation(count)
        for index in range(count):
            for offset in range(1, degree // 2 + 1):
                left, right = permutation[index], permutation[(index + offset) % count]
                couplings[left, right] = couplings[right, left] = strength * random.choice([-1., 1.])
        if degree % 2:
            for index in range(count // 2):
                left, right = permutation[index], permutation[index + count // 2]
                couplings[left, right] = couplings[right, left] = strength * random.choice([-1., 1.])
        fields = random.normal(0, 0.02, count)
    order = random.permutation(count)
    gauge = random.choice([-1., 1.], count)
    couplings = couplings[np.ix_(order, order)] * gauge[:, None] * gauge[None, :]
    fields = fields[order] * gauge
    return {"n": count, "couplings": couplings.tolist(), "fields": fields.tolist()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission")
    parser.add_argument("--label", required=True)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--generate-only", action="store_true")
    arguments = parser.parse_args()
    directory = ROOT / "concept_1" / "adversary" / arguments.label
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "challenge_space.json"
    if path.exists():
        cases = json.loads(path.read_text())
    else:
        cases = []
        grid = {"interacting_regions": (0.05, 0.15, 0.4, 0.8),
                "nonuniform_regions": (0.10, 0.25, 0.5, 0.9),
                "frustrated_cages": (0.8, 1.4, 2.3, 3.5)}
        for family_index, (family, strengths) in enumerate(grid.items()):
            for strength_index, strength in enumerate(strengths):
                for variant in range(3):
                    seed = 981547 + 1019 * family_index + 101 * strength_index + 11 * variant
                    cases.append({"id": family + "_" + str(strength_index) + "_" + str(variant),
                                  "family": family, "strength": strength, "seed": seed,
                                  "variant": variant, "instance": challenge(family, seed, strength, variant)})
        path.write_text(json.dumps(cases))
        (directory / "preregistration.json").write_text(json.dumps({
            "challenge_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "count": len(cases), "seed": 981547,
            "motivation": "Break independence of competing local sectors, broaden within-region bond disorder, and introduce overlapping frustrated cycles without changing spin count, artifact, or resources.",
            "absolute_gates": {"case_kl_diagnostic": 0.04, "minimum_ess": 0.25},
            "note": "A single-case KL is diagnostic, not an aggregate task failure. No new task targets are set by this audit."
        }, indent=2))
    if arguments.generate_only:
        return
    submission = EVALUATOR.validate_submission(arguments.submission)
    if (directory / "results.json").exists():
        raise ValueError("do not overwrite an earlier audit")
    results = []
    with ProcessPoolExecutor(max_workers=arguments.workers) as executor:
        pending = [executor.submit(worker, str(submission), case) for case in cases]
        for future in as_completed(pending):
            result = future.result()
            result["compression_gap_over_004"] = result.get("kl", 0) > 0.04
            results.append(result)
            (directory / "results.json").write_text(json.dumps(results, indent=2))
            print(json.dumps(result), flush=True)
    valid = [result for result in results if result["valid"]]
    summary = {"count": len(results), "valid": len(valid),
               "mean_kl": float(np.mean([result["kl"] for result in valid])) if valid else None,
               "worst_kl": max((result["kl"] for result in valid), default=None),
               "worst_ess": min((result["ess"] for result in valid), default=None),
               "tail_failures": sum(result["ess"] < 0.25 for result in valid),
               "kl_over_004": sum(result["compression_gap_over_004"] for result in results),
               "families": {family: {"mean_kl": float(np.mean([result["kl"] for result in valid if result["family"] == family])),
                                      "tail_failures": sum(result["ess"] < 0.25 for result in valid if result["family"] == family)}
                            for family in sorted({result["family"] for result in valid})},
               "submission": str(submission)}
    (directory / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()
