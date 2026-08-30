"""Measure coarse/full linear instabilities only in sandboxed child processes."""

import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "BLIS_NUM_THREADS"):
    os.environ[variable] = "1"
sys.dont_write_bytecode = True
import numpy as np

PENDING = Path(__file__).resolve().parent
ROOT = PENDING.parents[1]
sys.path.insert(0, str(ROOT / "evaluator"))
import evaluate


def main():
    tempfile.tempdir = str(PENDING / "scratch")
    selection = json.loads((PENDING / "selection.json").read_text())
    reports = []
    for probe_id in selection["replacements"].values():
        with np.load(PENDING / "cases" / probe_id / "instance.npz", allow_pickle=False) as archive:
            instance = {key: archive[key] for key in evaluate.INPUT_KEYS}
        output, execution = evaluate.run_candidate(PENDING / "diagnostic", instance)
        report = {"probe_id": probe_id, "execution": execution}
        if output is not None:
            report.update(full_linear_eigenvalues=output["delta"][0, :3].tolist(),
                          reduced_linear_eigenvalues=output["delta"][1, :3].tolist(),
                          reduced_frequencies=int(output["delta"][2, 0]))
        reports.append(report)
        print(json.dumps(report), flush=True)
    result = {"actual_v3_code_sha256": hashlib.sha256((PENDING / "diagnostic" / "v3.py").read_bytes()).hexdigest(),
              "diagnostic_only_not_a_solver_submission": True,
              "candidate_code_imported_only_in_sandbox_child": True, "cases": reports}
    (PENDING / "linear_diagnostic.json").write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
