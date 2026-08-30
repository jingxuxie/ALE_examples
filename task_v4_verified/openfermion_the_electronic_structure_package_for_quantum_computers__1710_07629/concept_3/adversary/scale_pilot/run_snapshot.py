"""Run only the captured binary in the existing isolation helper; labels excluded."""

import json
import os
from pathlib import Path
import sys
import tempfile

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "BLIS_NUM_THREADS"):
    os.environ[variable] = "1"
PILOT = Path(__file__).resolve().parent
ROOT = PILOT.parents[1]
sys.path.insert(0, str(ROOT / "evaluator"))

import numpy as np

from evaluate import run_guarded
from scoring import parse_predictions


def main():
    allowed = sorted(os.sched_getaffinity(0))
    os.sched_setaffinity(0, {allowed[240 % len(allowed)]})
    settings = json.loads((ROOT / "evaluator/settings.json").read_text())
    (PILOT / "runs").mkdir(exist_ok=True)
    report = {"site_counts": {}, "wall_limit": 25, "cpu_limit": 25,
              "memory_mb": 2048, "affinity": sorted(os.sched_getaffinity(0)),
              "adaptation": "none", "default_steps": 100, "default_tolerance": 1e-7}
    for size in (10, 12):
        with np.load(PILOT / f"inputs_{size}.npz", allow_pickle=False) as archive:
            inputs = dict(archive)
        with tempfile.TemporaryDirectory(prefix=f"native{size}-", dir=PILOT / "runs") as temporary:
            scratch = Path(temporary)
            np.savez_compressed(scratch / "inputs.npz", **inputs)
            request = {"schema_version": 1, "inputs": str(scratch / "inputs.npz"),
                       "n_instances": 8, "target_order": ["charge_gap", "spin_gap"]}
            (scratch / "request.json").write_text(json.dumps(request))
            runtime = run_guarded(["/usr/bin/python3", str(PILOT / "snapshot/solver.py"),
                str(scratch / "request.json"), str(scratch / "predictions.json")], {},
                PILOT / "snapshot", scratch, settings)
            result = {"actual_cli_runtime": runtime, "count": 8}
            if runtime["failure"] is None:
                predictions = parse_predictions((scratch / "predictions.json").read_text(), 8)
                result["predictions"] = predictions.tolist()
            probe_code = (PILOT / "probe.py").read_text()
            runtime = run_guarded(["/usr/bin/python3", "-c", probe_code,
                str(scratch / "request.json"), str(scratch / "timing.json")], {},
                PILOT / "snapshot", scratch, settings)
            result["instrumented_runtime"] = runtime
            result["rows"] = json.loads((scratch / "timing.json").read_text()) if (scratch / "timing.json").exists() else []
            report["site_counts"][str(size)] = result
            (PILOT / "snapshot_runtime.json").write_text(json.dumps(report, indent=2) + "\n")
            print(json.dumps({"size": size, "actual_cli": result["actual_cli_runtime"],
                              "instrumented": runtime, "completed_rows": len(result["rows"])}), flush=True)
    print("SNAPSHOT_TIMING_COMPLETE", flush=True)


if __name__ == "__main__":
    main()
