import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "workspace"))
from physics import design_cost, load_assets


def allocate(features, candidates, contract):
    batches = np.zeros(len(candidates), dtype=np.int64)
    lengths = np.array([len(circuit["germ"]) * circuit["repetitions"] for circuit in candidates])
    increment = 4
    shot_cost = contract["shots_per_batch"] * (lengths + contract["reset_ticks"])
    information = np.eye(14) * 1e-3
    for iteration in range(2000):
        remaining = contract["execution_budget_ticks"] - design_cost(batches, candidates, contract)
        costs = shot_cost * increment + (batches == 0) * contract["setup_ticks"]
        legal = (costs <= remaining) & (batches + increment <= contract["max_batches_per_circuit"])
        if np.count_nonzero(batches) >= contract["max_distinct_circuits"]:
            legal &= batches > 0
        if not np.any(legal):
            break
        leverage = np.einsum("ci,ij,cj->c", features, np.linalg.inv(information), features, optimize=True)
        gains = np.log1p(increment * contract["shots_per_batch"] * np.maximum(leverage, 0)) / costs
        gains[~legal] = -np.inf
        selected = int(np.argmax(gains))
        batches[selected] += increment
        information += increment * contract["shots_per_batch"] * np.outer(features[selected], features[selected])
    return batches


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    candidates, contract = load_assets(root)
    nominal = np.load(root / "input/development.npz")["nominal_features"]
    batches = allocate(nominal, candidates, contract)
    Path(args.output).write_text(json.dumps({"batches": batches.tolist()}) + "\n")
    print(json.dumps({"cost": design_cost(batches, candidates, contract),
                      "distinct_circuits": int(np.count_nonzero(batches))}))


if __name__ == "__main__":
    main()
