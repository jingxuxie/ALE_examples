"""Privileged generation-time exploration, never a fresh-agent attempt."""

import os
for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "workspace"))
from simulator import compare


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--trials", type=int, default=80)
    parser.add_argument("--seed", type=int, default=230614887)
    parser.add_argument("--output", type=Path, required=True)
    options = parser.parse_args()
    random = np.random.default_rng(options.seed)
    started = time.monotonic()
    records = []
    for trial in range(options.trials):
        depth = int(random.choice([12, 16, 20, 24, 28, 32, 40, 48]))
        if trial < 36:
            angle = 0.4 + (trial % 12) * 0.09
            depth = [16, 24, 36][trial // 12]
            angles = np.full(depth, angle)
        elif trial % 3 == 0:
            angles = random.uniform(0.15, 1.42, depth)
        else:
            center = random.uniform(0.5, 1.2)
            amplitude = random.uniform(0.02, min(center - 0.11, 1.46 - center))
            angles = center + amplitude * np.sin(np.linspace(0, random.uniform(2, 20), depth) + random.uniform(0, 6.28))
        result = compare(angles)
        for observable, metrics in result["metrics"].items():
            merit = min(metrics["error"] / 0.12, 0.01 / max(metrics["spread"], 1e-8))
            records.append({"trial": trial, "angles": angles.tolist(), "observable": observable,
                            "merit": merit, **metrics, "result": result})
        records.sort(key=lambda record: record["merit"], reverse=True)
        records = records[:30]
        options.output.write_text(json.dumps({"trials": trial + 1, "elapsed": time.monotonic() - started,
                                              "best": records}, indent=2) + "\n")
        best = records[0]
        print(json.dumps({"trial": trial, "depth": depth, "elapsed": round(time.monotonic() - started, 2),
                          "best": {key: best[key] for key in ("trial", "observable", "error", "spread", "merit")}}), flush=True)


if __name__ == "__main__":
    main()
