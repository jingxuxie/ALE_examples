import argparse
import json
import math
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "participant/workspace"))
import checker
from target_method import fft_complementary_polynomial


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--trials", type=int, default=96)
    args = parser.parse_args()
    directory = ROOT / "adversary/private_search"
    directory.mkdir(exist_ok=True)
    candidate_dir = directory / "candidate"
    candidate_dir.mkdir(exist_ok=True)
    best_dir = directory / "best"
    best_dir.mkdir(exist_ok=True)
    records = []
    best_score = -1
    started = time.monotonic()
    for trial in range(args.trials):
        degree = (32, 40, 48)[trial % 3]
        seed = 68217000 + trial
        rng = np.random.default_rng(seed)
        polynomial = np.exp(rng.normal(0, (trial % 4) * 0.15, degree + 1)) * np.exp(1j * rng.uniform(-np.pi, np.pi, degree + 1))
        polynomial *= (0.74 + 0.01 * (trial % 6)) / np.max(np.abs(np.fft.fft(polynomial, 65536)))
        certificate = 0.8 * fft_complementary_polynomial(polynomial / 0.8, tolerance=0, num_modes=65536)
        artifact = {"P": [[float(value.real), float(value.imag)] for value in polynomial],
                    "H": [[float(value.real), float(value.imag)] for value in certificate]}
        (candidate_dir / "counterexample.json").write_text(json.dumps(artifact))
        result = checker.evaluate(candidate_dir)
        records.append({"seed": seed, "degree": degree, "score": result["core_score"],
                        "minimum_rms_error": result.get("minimum_rms_error"), "admissible": result.get("admissible", False), "reason": result["reason"]})
        if result["core_score"] > best_score:
            best_score = result["core_score"]
            (best_dir / "counterexample.json").write_text(json.dumps(artifact))
            (best_dir / "score.json").write_text(json.dumps(result, indent=2))
        if trial % 12 == 0:
            print(trial, best_score, flush=True)
        if result["passed"]:
            break
    report = {"trials": len(records), "admissible": sum(record["admissible"] for record in records),
              "best_score": best_score, "passing_witness_found": best_score >= 1,
              "elapsed_seconds": time.monotonic() - started, "records": records}
    (directory / "report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps({key: value for key, value in report.items() if key != "records"}), flush=True)


if __name__ == "__main__":
    main()
