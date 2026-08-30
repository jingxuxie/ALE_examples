"""Finish only the already-selected n12 rows absent from the timed batch."""

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


def main():
    allowed = sorted(os.sched_getaffinity(0))
    os.sched_setaffinity(0, {allowed[240 % len(allowed)]})
    settings = json.loads((ROOT / "evaluator/settings.json").read_text())
    with np.load(PILOT / "inputs_12.npz", allow_pickle=False) as archive:
        inputs = dict(archive)
    original = json.loads((PILOT / "snapshot_runtime.json").read_text())["site_counts"]["12"]
    rows = original["rows"][:]
    completed = {row["index"] for row in rows}
    additional = []
    for index in range(8):
        if index in completed:
            continue
        with tempfile.TemporaryDirectory(prefix="complete-", dir=PILOT / "runs") as temporary:
            scratch = Path(temporary)
            np.savez_compressed(scratch / "inputs.npz", **{key: value[index:index + 1] for key, value in inputs.items()})
            (scratch / "request.json").write_text(json.dumps({"schema_version": 1,
                "inputs": str(scratch / "inputs.npz"), "n_instances": 1,
                "target_order": ["charge_gap", "spin_gap"]}))
            runtime = run_guarded(["/usr/bin/python3", "-c", (PILOT / "probe.py").read_text(),
                str(scratch / "request.json"), str(scratch / "timing.json")], {},
                PILOT / "snapshot", scratch, settings)
            additional.append({"index": index, "runtime": runtime})
            if runtime["failure"]:
                raise RuntimeError(runtime)
            row = json.loads((scratch / "timing.json").read_text())[0]
            row["index"] = index
            rows.append(row)
            print(json.dumps({key: row[key] for key in ("index", "family", "cpu_seconds", "predictions")}), flush=True)
    report = {"rows": sorted(rows, key=lambda row: row["index"]), "extra_single_row_runs": additional,
              "new_cases_generated": 0, "purpose": "quality for rows unfinished by the actual 25-second batch"}
    (PILOT / "complete_12.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
