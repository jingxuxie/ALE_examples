import argparse
import hashlib
import json
import random
import secrets
import time
from pathlib import Path

import numpy as np

from core import circuit_weights, summarize
from design import hardware, random_layers, search


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", type=int, default=96)
    parser.add_argument("--iterations", type=int, default=6000)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    seed = secrets.randbits(128)
    rng = random.Random(seed)
    records = []
    champions = []
    started = time.perf_counter()
    for base, depths in zip(hardware(), ((10, 12, 14), (8, 10, 12), (10, 12, 14))):
        family_records = []
        for depth in depths:
            family = dict(base, max_rounds=depth, max_cx=int(0.42 * base["n"] * depth))
            minima = []
            means = []
            best_key = None
            for _ in range(args.samples):
                layers = random_layers(family, rng)
                weights = circuit_weights(family["n"], layers)
                minimum = [int(samples.min()) for strata in weights for samples in strata]
                average = [float(samples.mean()) for strata in weights for samples in strata]
                minima.append(minimum)
                means.append(average)
                key = (min(minimum), sum(minimum), sum(average))
                if best_key is None or key > best_key:
                    best_key = key
                    best = {"family": family["id"], "layers": layers}
            record = {"family": family["id"], "max_rounds": depth, "max_cx": family["max_cx"],
                      "samples": args.samples, "minima_quantiles": np.quantile(minima, [0, .5, .9, 1], axis=0).tolist(),
                      "means_quantiles": np.quantile(means, [0, .5, .9, 1], axis=0).tolist()}
            print(json.dumps(record), flush=True)
            family_records.append(record)
            champions.append(best)
        records.extend(family_records)
    report = {"phase": "pre-freeze random pilot", "seed": str(seed),
              "seed_sha256": hashlib.sha256(str(seed).encode()).hexdigest(),
              "runtime_seconds": time.perf_counter() - started, "records": records}
    (root / "evaluator/hidden/pilot_results.json").write_text(json.dumps(report, indent=2) + "\n")
    (root / "evaluator/hidden/pilot_circuits.json").write_text(json.dumps(champions) + "\n")


if __name__ == "__main__":
    main()
