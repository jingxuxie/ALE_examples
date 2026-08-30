import argparse
import concurrent.futures
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def worker(seed, count):
    os.environ["ASSETS"] = str(ROOT / "participant")
    sys.path.insert(0, str(ROOT / "participant/workspace"))
    sys.path.insert(0, str(ROOT / "champions/generation_2"))
    import numpy as np
    from search import make_artifact
    from tail_search import assess
    import checker

    directory = ROOT / "adversary/final_compact_refinement" / f"seed_{seed}"
    directory.mkdir(parents=True, exist_ok=True)
    initial = ROOT / "adversary/second_champion_stress/degree_12_seed_639405/tail_best.json"
    polynomial = np.array([complex(*pair) for pair in json.loads(initial.read_text())["P"]])
    best = assess(polynomial)[0]
    best_polynomial = polynomial.copy()
    make_artifact(polynomial, str(directory / "counterexample.json"))
    random = np.random.default_rng(seed)
    records = []
    admitted = 0
    started = time.monotonic()
    for trial in range(count):
        candidate = best_polynomial.copy()
        phase_scale = (0.000001, 0.002, 0.02, 0.1, 0.4)[trial % 5]
        amplitude_scale = (0.000001, 0.001, 0.01, 0.03, 0.1)[trial % 5]
        candidate *= np.exp(1j * random.normal(0, phase_scale, len(candidate)))
        candidate *= np.exp(random.normal(0, amplitude_scale, len(candidate)))
        if trial % 7 == 0:
            candidate *= np.exp(1j * random.uniform(-np.pi, np.pi))
        desired_max = random.uniform(0.69, 0.794)
        candidate *= desired_max / np.max(np.abs(np.fft.fft(candidate, 4096)))
        energy = np.vdot(candidate, candidate).real
        rms = np.sqrt(energy / len(candidate))
        if not 0.08 <= energy <= 0.30 or abs(np.sum(candidate**2)) > 0.8 * energy:
            continue
        magnitudes = np.abs(candidate)
        if np.min(magnitudes) < 0.25 * rms or np.max(magnitudes) > 4 * rms:
            continue
        admitted += 1
        score, margin, errors = assess(candidate)
        if score > best and margin >= 1e-8:
            make_artifact(candidate, str(directory / "candidate.json"))
            candidate_data = json.loads((directory / "candidate.json").read_text())
            report = checker.evaluate_artifact(candidate_data) if hasattr(checker, "evaluate_artifact") else None
            if report is None:
                temporary = directory / "candidate_submission"
                temporary.mkdir(exist_ok=True)
                (temporary / "counterexample.json").write_text(json.dumps(candidate_data))
                result = subprocess.run([sys.executable, str(ROOT / "evaluator/evaluate.py"),
                                         "--submission", str(temporary)], capture_output=True,
                                        text=True, timeout=65, check=True)
                report = json.loads(result.stdout)
            if not report.get("admissible", False):
                continue
            best = report["minimum_rms_error"]
            best_polynomial = candidate.copy()
            (directory / "counterexample.json").write_text(json.dumps(candidate_data) + "\n")
            (directory / "score.json").write_text(json.dumps(report, indent=2) + "\n")
            records.append({"trial": trial, "minimum_rms_error": best, "guard": margin,
                            "energy": float(energy), "fast_errors": errors})
            (directory / "improvements.json").write_text(json.dumps(records, indent=2) + "\n")
            print(seed, trial, best, flush=True)
            if report["passed"]:
                break
    if not (directory / "score.json").exists():
        result = subprocess.run([sys.executable, str(ROOT / "evaluator/evaluate.py"),
                                 "--submission", str(directory)], capture_output=True,
                                text=True, timeout=65, check=True)
        (directory / "score.json").write_text(result.stdout)
    report = json.loads((directory / "score.json").read_text())
    return {"seed": seed, "trials": trial + 1, "screened_admissible_candidates": admitted,
            "minimum_rms_error": report["minimum_rms_error"], "core_score": report["core_score"],
            "admissible": report["admissible"], "passed": report["passed"],
            "elapsed_seconds": time.monotonic() - started}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=20000)
    args = parser.parse_args()
    seeds = (906271, 731248, 591036, 482917)
    with concurrent.futures.ProcessPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(worker, seed, args.count) for seed in seeds]
        records = [future.result() for future in futures]
    report = {"degree": 12, "method": "privileged champion-seeded amplitude/phase refinement",
              "runs": records, "total_trials": sum(record["trials"] for record in records),
              "best_minimum_rms_error": max(record["minimum_rms_error"] for record in records),
              "passing_witness_known": any(record["passed"] for record in records)}
    (ROOT / "adversary/final_compact_refinement/report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
