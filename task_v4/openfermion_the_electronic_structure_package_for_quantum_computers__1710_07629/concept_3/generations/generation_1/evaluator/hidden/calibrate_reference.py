"""Two fixed pilot labels check the new eigsh workload before batch generation."""

import json
import os
from pathlib import Path
import sys

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"
ROOT = Path(__file__).resolve().parents[2]
PILOT = ROOT / "evaluator/hidden/pilot_reference"

import numpy as np

from native_reference import label


def main():
    allowed = sorted(os.sched_getaffinity(0))
    os.sched_setaffinity(0, {allowed[240 % len(allowed)]})
    with np.load(PILOT / "inputs_12.npz", allow_pickle=False) as archive:
        data = dict(archive)
    with np.load(PILOT / "labels_12.npz", allow_pickle=False) as archive:
        expected = archive["gaps"]
    rows = []
    for index in (0, 2):
        result = label(data["hopping"][index], data["interaction"][index], data["potential"][index], seed=771091)
        result["index"] = index
        result["gap_error"] = float(np.max(abs(np.array(result["gaps"]) - expected[index])))
        assert result["gap_error"] < 2e-8
        rows.append(result)
        print(json.dumps({key: result[key] for key in ("index", "gap_error", "cpu_seconds")}), flush=True)
    (ROOT / "evaluator/hidden/reference_calibration.json").write_text(json.dumps({"rows": rows, "passed": True}, indent=2) + "\n")


if __name__ == "__main__":
    main()
