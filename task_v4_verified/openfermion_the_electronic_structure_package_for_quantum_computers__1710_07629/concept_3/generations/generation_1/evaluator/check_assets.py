"""Trusted checks of real canary isolation and a small native quality batch."""

import argparse
import json
import os
from pathlib import Path
import sys
import tempfile

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"

import numpy as np

from evaluate import INPUT_KEYS, ROOT, read_output, run_guarded
from scoring import parse_predictions, score_predictions


def check_isolation(settings):
    participant = ROOT / "participant"
    private_paths = [ROOT / "evaluator/hidden/isolation_canary.txt",
                     participant.parents[3] / "private/generation_canary.txt", ROOT / "status.json"]
    assert all(path.is_file() for path in private_paths), "Canaries must exist outside the sandbox"
    with tempfile.TemporaryDirectory(prefix="audit-", dir=ROOT / "evaluator/runs") as directory:
        scratch = Path(directory).resolve()
        runtime = run_guarded([sys.executable, "-B", str(participant / "workspace/audit_isolation.py"), str(scratch)],
                              {}, participant / "workspace", scratch, settings)
        assert runtime["failure"] is None, runtime
        audit = json.loads((scratch / "isolation_audit.json").read_text())
        assert audit["participant_readable"] and audit["private_reads_denied"]
        assert all(row["result"] == "PermissionError" for row in audit["probes"]), audit
    report = {"all_private_files_exist": True, "audit": audit, "runtime": runtime, "passed": True}
    (ROOT / "adversary/isolation_audit_report.json").write_text(json.dumps(report, indent=2) + "\n")
    print("isolation", json.dumps(report))


def check_native(settings):
    with np.load(ROOT / "participant/input/validation.npz", allow_pickle=False) as archive:
        data = dict(archive)
    indices = [int(np.flatnonzero((data["family"] == family) & (data["n_sites"] == size))[0])
               for family in range(4) for size in (10, 12)]
    submission = ROOT / "participant/baseline_exact"
    with tempfile.TemporaryDirectory(prefix="native-quality-", dir=ROOT / "evaluator/runs") as directory:
        scratch = Path(directory).resolve()
        input_path = scratch / "inputs.npz"
        request_path = scratch / "request.json"
        output_path = scratch / "predictions.json"
        np.savez_compressed(input_path, **{key: data[key][indices] for key in INPUT_KEYS})
        request_path.write_text(json.dumps({"schema_version": 1, "inputs": str(input_path),
            "n_instances": len(indices), "target_order": ["charge_gap", "spin_gap"]}) + "\n")
        runtime = run_guarded([sys.executable, "-B", str(submission / "solver.py"), str(request_path), str(output_path)],
                              {}, submission, scratch, settings)
        report = {"validation_indices": indices, "count": len(indices), "runtime": runtime,
                  "full_batch_resource_claim": False, "passed": False}
        if runtime["failure"] is None:
            predictions = parse_predictions(read_output(output_path, settings["prediction_bytes"]), len(indices))
            report.update(score_predictions(predictions, data["gaps"][indices], data["family"][indices], settings))
            report["predictions"] = predictions.tolist()
            report["labels"] = data["gaps"][indices].tolist()
            report["max_abs_error"] = float(np.max(np.abs(predictions - data["gaps"][indices])))
            report["passed"] = report["accuracy_passed"]
    (ROOT / "attempts/exact_small_quality.json").write_text(json.dumps(report, indent=2) + "\n")
    print("native", json.dumps(report))
    assert report["passed"], report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", choices=("isolation", "native", "both"), default="both")
    arguments = parser.parse_args()
    settings = json.loads((ROOT / "evaluator/settings.json").read_text())
    (ROOT / "evaluator/runs").mkdir(exist_ok=True)
    if arguments.only in ("isolation", "both"):
        check_isolation(settings)
    if arguments.only in ("native", "both"):
        check_native(settings)


if __name__ == "__main__":
    main()
