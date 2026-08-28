import os

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import argparse
import json
from pathlib import Path
import sys
import time

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evaluator import evaluate, run_solver
from metrics import grade, measure
from solver import reconstruct


ROOT = Path(__file__).resolve().parents[2]


def calibrate(directory, ablations=False):
    directory = Path(directory).resolve()
    manifest_path = directory / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    evidence = []
    for record in manifest["cases"]:
        with np.load(directory / record["input"], allow_pickle=False) as archive:
            data = dict(archive)
        with np.load(directory / record["truth"], allow_pickle=False) as archive:
            truth = dict(archive)
        calibration = {}
        entry = dict(id=record["id"], family=record["family"])
        for name, filename in (("reference", "solver.py"), ("weak", "weak_solver.py")):
            output = directory / record["id"] / f"{name}_prediction.npz"
            prediction, runtime = run_solver(ROOT / "private" / "reference" / filename, directory / record["input"], output)
            if prediction is None:
                raise RuntimeError(f"{name} failed {record['id']}: {runtime}")
            metrics = measure(prediction, truth, float(data["recovery_floor"]))
            calibration[name] = metrics
            entry[name] = dict(**metrics, **runtime)
        record["calibration"] = calibration
        for name in ("reference", "weak"):
            entry[name].update(grade(calibration[name], calibration))
        if ablations:
            for name, options in (("one_pass", dict(rounds=1)), ("no_joint_refit", dict(joint=False))):
                start = time.monotonic()
                prediction = reconstruct(data, **options)
                entry[name] = dict(**grade(measure(prediction, truth, float(data["recovery_floor"])), calibration), runtime_seconds=time.monotonic() - start)
        evidence.append(entry)
        print(f"{manifest['pool']}/{record['id']} {record['family']}: strong={entry['reference']['score']:.6f} F1={entry['reference']['recovery_score']:.6f} weak={entry['weak']['score']:.6f} time={entry['reference']['runtime_seconds']:.2f}s", flush=True)
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    minimum_reference = min(case["reference"]["score"] for case in evidence)
    maximum_weak = max(case["weak"]["score"] for case in evidence)
    maximum_reference_loss = max(case["reference"]["loss"] for case in evidence)
    checks = dict(minimum_reference_score=minimum_reference, maximum_weak_score=maximum_weak, maximum_reference_uncapped_loss=maximum_reference_loss, all_reference_above_0_9=minimum_reference > 0.9, all_weak_below_0_2=maximum_weak < 0.2, all_reference_raw_loss_below_0_1=maximum_reference_loss < 0.1, all_independent_observation_errors_below_2e_12=all(case["independent_observation_max_error"] < 2e-12 for case in manifest["cases"]))
    report = dict(pool=manifest["pool"], region=manifest["region"], checks=checks, cases=evidence, dense_resource_estimates=[dict(qubits=qubits, float64_probability_vector_bytes=8 * 4**qubits, walsh_additions=2 * qubits * 4**qubits, years_at_1e12_additions_per_second=2 * qubits * 4**qubits / 1e12 / (365.25 * 86400)) for qubits in (40, 64, 100)])
    (directory / "benchmark.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    if not all(value for key, value in checks.items() if key.startswith("all_")):
        raise AssertionError(checks)
    manifest["calibrated"] = True
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(checks), flush=True)
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pool", choices=("core", "challenge"), default="core")
    parser.add_argument("--case-root", type=Path)
    parser.add_argument("--ablations", action="store_true")
    parser.add_argument("--verify-cli", action="store_true")
    args = parser.parse_args()
    directory = args.case_root or ROOT / "private" / ("reference/core" if args.pool == "core" else "challenge_pool")
    calibrate(directory, args.ablations)
    if args.verify_cli:
        for name, filename in (("reference", "solver.py"), ("weak", "weak_solver.py")):
            result = evaluate(ROOT / "private" / "reference" / filename, directory)
            (directory / f"{name}_report.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    main()
