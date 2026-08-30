"""Public-validation timing of two standard ED implementations in isolation."""

import argparse
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "evaluator"))

import numpy as np

from evaluate import run_guarded
from scoring import parse_predictions, score_predictions


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tolerance", type=float, default=1e-5)
    parser.add_argument("--ncv", type=int, default=20)
    parser.add_argument("--report", type=Path, default=ROOT / "attempts/direct_ed_timing.json")
    arguments = parser.parse_args()
    settings = json.loads((ROOT / "evaluator/settings.json").read_text())
    with np.load(ROOT / "participant/input/validation.npz", allow_pickle=False) as archive:
        data = dict(archive)
    submission = ROOT / "attempts/direct_ed"
    rows = []
    for family in range(4):
        for size in (8, 10):
            rows.extend(np.flatnonzero((data["family"] == family) & (data["n_sites"] == size))[:2])
    report = {"split": "public_validation_only", "tol": arguments.tolerance,
              "ncv": arguments.ncv, "pilots": {}}
    for method in ("csr", "tensor"):
        with tempfile.TemporaryDirectory(prefix="ed-pilot-", dir=ROOT / "evaluator/runs") as temporary:
            scratch = Path(temporary)
            np.savez_compressed(scratch / "inputs.npz", **{key: value[rows] for key, value in data.items() if key != "gaps"})
            (scratch / "request.json").write_text(json.dumps({"schema_version": 1,
                "inputs": str(scratch / "inputs.npz"), "n_instances": len(rows),
                "target_order": ["charge_gap", "spin_gap"], "method": method,
                "tolerance": arguments.tolerance, "ncv": arguments.ncv}))
            runtime = run_guarded(["/usr/bin/python3", str(submission / "solver.py"),
                str(scratch / "request.json"), str(scratch / "predictions.json")], {}, submission, scratch,
                dict(settings, wall_seconds=180.0, cpu_seconds=180))
            result = {"runtime": runtime, "count": len(rows)}
            if runtime["failure"] is None:
                predictions = parse_predictions((scratch / "predictions.json").read_text(), len(rows))
                result.update(score_predictions(predictions, data["gaps"][rows], data["family"][rows], settings))
            report["pilots"][method] = result
            print(method, runtime, flush=True)
    best_method = min(report["pilots"], key=lambda method: report["pilots"][method]["runtime"]["wall_seconds"])
    with tempfile.TemporaryDirectory(prefix="ed-full-", dir=ROOT / "evaluator/runs") as temporary:
        scratch = Path(temporary)
        np.savez_compressed(scratch / "inputs.npz", **{key: value for key, value in data.items() if key != "gaps"})
        (scratch / "request.json").write_text(json.dumps({"schema_version": 1,
            "inputs": str(scratch / "inputs.npz"), "n_instances": 256,
            "target_order": ["charge_gap", "spin_gap"], "method": best_method,
            "tolerance": arguments.tolerance, "ncv": arguments.ncv}))
        runtime = run_guarded(["/usr/bin/python3", str(submission / "solver.py"),
            str(scratch / "request.json"), str(scratch / "predictions.json")], {}, submission, scratch,
            dict(settings, wall_seconds=600.0, cpu_seconds=600))
        report["full_validation"] = {"method": best_method, "runtime": runtime,
                                     "budget_matched": False, "purpose": "measure complete-batch cost"}
        if runtime["failure"] is None:
            predictions = parse_predictions((scratch / "predictions.json").read_text(), 256)
            report["full_validation"].update(score_predictions(predictions, data["gaps"], data["family"], settings))
    arguments.report.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
