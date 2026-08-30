import argparse
import concurrent.futures
import json
import os
from pathlib import Path
import sys
import time

for variable in ("OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "OMP_NUM_THREADS"):
    os.environ[variable] = "1"

import numpy as np

from physics import observables


def evaluate_order(job):
    bank_index, candidate, order, fields, scales = job
    results = [observables(scale * np.array(fields)[order]) for scale in scales]
    return bank_index, candidate, order, [result["r"] for result in results], [result["f"] for result in results]


def make_orders(fields, count, seed):
    generator = np.random.default_rng(seed)
    length = len(fields)
    sorted_order = np.argsort(fields)
    orders = [sorted_order.copy(), np.r_[sorted_order[::2], sorted_order[1::2][::-1]]]
    for candidate in range(count - len(orders)):
        if candidate % 4 == 0:
            order = generator.permutation(length)
        elif candidate % 4 == 1:
            order = sorted_order.copy()
            for move in range(generator.integers(1, length)):
                left, right = generator.choice(length, 2, replace=False)
                order[left], order[right] = order[right], order[left]
        elif candidate % 4 == 2:
            values = np.asarray(fields)
            noise = generator.normal(size=length) * generator.uniform(0.1, 5.0)
            order = np.argsort(values + noise)
        else:
            blocks = np.array_split(sorted_order, generator.integers(2, 6))
            generator.shuffle(blocks)
            order = np.concatenate([generator.permutation(block) for block in blocks])
        orders.append(order)
    return [order.tolist() for order in orders]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=600)
    parser.add_argument("--workers", type=int, default=8)
    arguments = parser.parse_args()
    root = Path(__file__).resolve().parents[1] / "concept_2"
    spec = json.loads((root / "evaluator/hidden/spec.json").read_text())
    adversary = root / "adversary"
    started = time.monotonic()
    jobs = []
    for bank_index, bank in enumerate(spec["banks"]):
        for candidate, order in enumerate(make_orders(bank["fields"], arguments.count, 8821 + bank_index)):
            jobs.append((bank_index, candidate, order, bank["fields"], spec["scales"]))
    arrays = {index: [] for index in range(len(spec["banks"]))}
    with (adversary / "layout_bank.jsonl").open("w") as archive:
        with concurrent.futures.ProcessPoolExecutor(max_workers=arguments.workers) as executor:
            for finished, result in enumerate(executor.map(evaluate_order, jobs, chunksize=2)):
                archive.write(json.dumps(result) + "\n")
                archive.flush()
                arrays[result[0]].append(result)
                if finished % 50 == 0:
                    print(json.dumps({"done": finished + 1, "total": len(jobs), "seconds": time.monotonic() - started}), flush=True)
    sys.path.insert(0, str(root / "evaluator"))
    from check import evaluate_design
    hidden_seeds = json.loads((root / "evaluator/hidden/seeds.json").read_text())["seeds"]
    final_layouts = []
    search_records = []
    for bank_index, bank in enumerate(spec["banks"]):
        entries = arrays[bank_index]
        ratios = np.array([entry[3] for entry in entries])
        fractions = np.array([entry[4] for entry in entries])
        differences = np.max(np.abs(ratios[:, None] - ratios[None, :]), axis=2)
        separation = np.min(fractions[:, None] - fractions[None, :], axis=2)
        surrogate = np.minimum(separation / 0.28, 0.02 / np.maximum(differences, 1e-12))
        pairs = np.dstack(np.unravel_index(np.argsort(surrogate, axis=None)[::-1][:100], surrogate.shape))[0]
        best = None
        local_spec = {**spec, "banks": [bank]}
        for high_index, low_index in pairs:
            design = {"layouts": [{"id": bank["id"], "high": entries[high_index][2], "low": entries[low_index][2]}]}
            result = evaluate_design(design, local_spec, hidden_seeds)
            if best is None or result["worst_family_score"] > best[0]["worst_family_score"]:
                best = result, design
            print(json.dumps({"bank": bank["id"], "worst": result["worst_family_score"], "passed": result["passed"]}), flush=True)
            if result["passed"]:
                break
        final_layouts.extend(best[1]["layouts"])
        search_records.append({"bank": bank["id"], "best": best[0], "searched_candidates": len(entries)})
        destination = adversary / "privileged_candidate"
        destination.mkdir(exist_ok=True)
        (destination / "design.json").write_text(json.dumps({"layouts": final_layouts}, indent=2) + "\n")
        (adversary / "search_results.json").write_text(json.dumps({"records": search_records, "seconds": time.monotonic() - started}, indent=2) + "\n")
    print(json.dumps({"finished": True, "seconds": time.monotonic() - started}), flush=True)


if __name__ == "__main__":
    main()
