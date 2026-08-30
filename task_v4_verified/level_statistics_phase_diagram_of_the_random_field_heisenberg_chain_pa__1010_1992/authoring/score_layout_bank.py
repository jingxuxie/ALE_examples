import concurrent.futures
import json
import os
from pathlib import Path
import sys
import time

for variable in ("OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "OMP_NUM_THREADS"):
    os.environ[variable] = "1"

import numpy as np

ROOT = Path(__file__).resolve().parents[1] / "concept_2"
sys.path.insert(0, str(ROOT / "evaluator"))
from check import evaluate_design


def score(job):
    bank_index, design, spec, seeds = job
    return bank_index, design, evaluate_design(design, spec, seeds)


def main():
    started = time.monotonic()
    spec = json.loads((ROOT / "evaluator/hidden/spec.json").read_text())
    seeds = json.loads((ROOT / "evaluator/hidden/seeds.json").read_text())["seeds"]
    entries = [json.loads(line) for line in (ROOT / "adversary/layout_bank.jsonl").read_text().splitlines()]
    jobs = []
    for bank_index, bank in enumerate(spec["banks"]):
        candidates = [entry for entry in entries if entry[0] == bank_index]
        ratios = np.array([entry[3] for entry in candidates])
        fractions = np.array([entry[4] for entry in candidates])
        gap = np.max(np.abs(ratios[:, None] - ratios[None, :]), axis=2)
        separation = np.min(fractions[:, None] - fractions[None, :], axis=2)
        surrogate = np.minimum(separation / 0.28, 0.02 / np.maximum(gap, 1e-12))
        pairs = np.dstack(np.unravel_index(np.argsort(surrogate, axis=None)[::-1][:80], surrogate.shape))[0]
        for high_index, low_index in pairs:
            design = {"layouts": [{"id": bank["id"], "high": candidates[high_index][2], "low": candidates[low_index][2]}]}
            jobs.append((bank_index, design, {**spec, "banks": [bank]}, seeds))
    best = {}
    records = []
    with (ROOT / "adversary/robust_pairs.jsonl").open("w") as archive:
        with concurrent.futures.ProcessPoolExecutor(max_workers=8) as executor:
            for finished, (bank_index, design, result) in enumerate(executor.map(score, jobs, chunksize=1)):
                record = {"bank_index": bank_index, "design": design, "result": result}
                records.append(record)
                archive.write(json.dumps(record) + "\n")
                archive.flush()
                if bank_index not in best or result["worst_family_score"] > best[bank_index]["result"]["worst_family_score"]:
                    best[bank_index] = record
                    destination = ROOT / "adversary/privileged_candidate"
                    destination.mkdir(exist_ok=True)
                    layouts = [best[index]["design"]["layouts"][0] for index in sorted(best)]
                    (destination / "design.json").write_text(json.dumps({"layouts": layouts}, indent=2) + "\n")
                if finished % 10 == 0:
                    print(json.dumps({"done": finished + 1, "total": len(jobs), "seconds": time.monotonic() - started,
                                      "best": {index: value["result"]["worst_family_score"] for index, value in best.items()}}), flush=True)
    summary = {"candidate_layouts": len(entries), "robust_pairs_tested": len(records),
               "best": best, "seconds": time.monotonic() - started,
               "passing_design_known": len(best) == len(spec["banks"]) and all(value["result"]["passed"] for value in best.values()),
               "root_causes": ["gap-ratio mismatch after field calibration perturbation", "insufficient dynamical-fraction contrast"]}
    (ROOT / "adversary/search_results.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({"finished": True, "passing": summary["passing_design_known"], "seconds": summary["seconds"]}), flush=True)


if __name__ == "__main__":
    main()
