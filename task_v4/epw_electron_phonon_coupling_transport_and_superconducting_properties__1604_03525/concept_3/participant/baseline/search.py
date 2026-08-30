import argparse
import json
import os
from pathlib import Path
import sys

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(variable, "1")

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "workspace"))

import numpy as np
from model import DIMENSION, FREQUENCIES, conductivity, diagnostics, write_witness


def baseline_pair():
    first = np.zeros((DIMENSION, DIMENSION))
    second = np.zeros_like(first)
    second[0, 4] = second[4, 0] = 0.15
    second[1, 5] = second[5, 1] = -0.15
    return first, second


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--trials", type=int, default=0)
    parser.add_argument("--seed", type=int, default=29)
    arguments = parser.parse_args()
    if not 0 <= arguments.trials <= 100000:
        parser.error("trials must lie between zero and 100000")
    first, best = baseline_pair()
    best_value = float(np.trace(conductivity(best)))
    generator = np.random.default_rng(arguments.seed)
    allowed = (FREQUENCIES[:, None] + FREQUENCIES[None, :]) % 2 == 0
    for _ in range(arguments.trials):
        proposal = generator.normal(size=(DIMENSION, DIMENSION))
        proposal = (proposal + proposal.T) * allowed / 2
        proposal[:2, :2] = 0
        proposal *= 0.35 / max(np.sum(np.abs(proposal)), 1e-12)
        value = float(np.trace(conductivity(proposal)))
        if value > best_value:
            best, best_value = proposal, value
    destination = Path(arguments.output)
    write_witness(destination / "witness.json", first, best)
    print(json.dumps(diagnostics(first, best), indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
