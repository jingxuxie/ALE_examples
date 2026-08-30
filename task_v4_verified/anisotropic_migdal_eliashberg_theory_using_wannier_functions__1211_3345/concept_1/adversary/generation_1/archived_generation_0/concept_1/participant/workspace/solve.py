"""Starting submission, identical to the damped self-consistency baseline."""

import argparse
import os
from pathlib import Path
import sys
import time

import numpy as np

sys.path.insert(0, os.environ.get("ALE_PUBLIC_INPUT", str(Path(__file__).resolve().parents[1] / "input")))
from eliashberg import Model, load_instance


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    started = time.process_time()
    instance = load_instance(args.input)
    model = Model(instance)
    delta = instance["initial_delta"].copy()
    for iteration in range(220):
        renormalization, mapped = model.map(delta)
        scale = np.maximum(np.max(np.abs(delta), axis=1), np.pi * model.temperature * 1e-10)
        residual = np.max(np.abs(delta - mapped) / scale[:, None])
        if residual < 5e-10 or time.process_time() - started > 7.0:
            break
        delta = 0.35 * delta + 0.65 * mapped
    renormalization = model.map(delta)[0]
    np.savez(args.output, delta=delta, z=renormalization)


if __name__ == "__main__":
    main()
