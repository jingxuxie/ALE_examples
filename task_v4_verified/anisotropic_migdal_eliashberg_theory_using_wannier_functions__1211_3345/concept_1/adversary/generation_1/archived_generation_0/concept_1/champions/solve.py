"""Same-budget executable witness, using only the candidate's public instance."""

import argparse
import os
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, os.environ.get("ALE_PUBLIC_INPUT", str(Path(__file__).resolve().parents[1] / "participant" / "input")))
from eliashberg import Model, load_instance
from solver_core import solve


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    instance = load_instance(args.input)
    delta, renormalization, information = solve(instance, Model(instance), cpu_budget=10.0)
    np.savez(args.output, delta=delta, z=renormalization)


if __name__ == "__main__":
    main()
