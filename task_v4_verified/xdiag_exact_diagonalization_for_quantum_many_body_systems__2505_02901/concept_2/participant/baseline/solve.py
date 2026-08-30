import argparse
import json
import os
from pathlib import Path
import sys
import time

for variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "BLIS_NUM_THREADS"):
    os.environ[variable] = "1"

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "workspace"))

import numpy as np
from simulate import load_problem, score


def admissible_rescale(candidate, specification):
    limits = np.asarray(specification["amplitude_limits"])
    jump_limits = np.asarray(specification["adjacent_jump_limits"])
    jumps = np.diff(np.vstack((np.zeros((1, 3)), candidate, np.zeros((1, 3)))), axis=0)
    exposure = specification["slice_duration"] * np.sum((candidate / limits) ** 2)
    scale = max(
        1.0,
        float(np.max(np.abs(candidate) / limits)) / 0.97,
        float(np.max(np.abs(jumps) / jump_limits)) / 0.97,
        float(np.sqrt(exposure / specification["normalized_control_exposure_limit"])) / 0.97,
    )
    return candidate / scale


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path(__file__).resolve().parents[1] / "input")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--trials", type=int, default=32)
    parser.add_argument("--seed", type=int, default=1729)
    arguments = parser.parse_args()
    start = time.monotonic()
    problem = load_problem(arguments.input)
    specification = problem[0]
    generator = np.random.default_rng(arguments.seed)
    best = np.zeros((specification["slices"], specification["channels"]))
    best_report = score(best, problem)
    amplitudes = np.asarray(specification["amplitude_limits"])
    for trial in range(arguments.trials):
        coarse = generator.normal(size=(8, 3))
        candidate = np.column_stack([
            np.interp(np.linspace(0, 7, specification["slices"]), np.arange(8), coarse[:, channel])
            for channel in range(3)
        ])
        candidate *= amplitudes[None, :] * (0.45 if trial % 2 else 0.8)
        if trial % 3 == 0:
            candidate = best + candidate * 0.4
        candidate = admissible_rescale(candidate, specification)
        report = score(candidate, problem)
        if report["core_score"] > best_report["core_score"]:
            best, best_report = candidate, report
    arguments.output.mkdir(parents=True, exist_ok=True)
    payload = {"schema_version": 1, "amplitudes": best.tolist()}
    (arguments.output / "pulse.json").write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n")
    best_report["elapsed_seconds"] = time.monotonic() - start
    best_report["trials"] = arguments.trials
    (arguments.output / "baseline_report.json").write_text(json.dumps(best_report, indent=2, allow_nan=False) + "\n")
    print(json.dumps(best_report, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
