"""Trusted audit controller; operator implementations remain in the sandbox."""

import json
import os
from pathlib import Path
import resource
import shutil
import sys
import tempfile
import time

STARTED = time.process_time()
for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "BLIS_NUM_THREADS"):
    os.environ[variable] = "1"
import numpy as np
from run_suite import CONCEPT, SIDECAR, digest, identities


def main():
    before = identities()
    source = SIDECAR / "operator_audit_submission"
    source.mkdir()
    shutil.copyfile(SIDECAR / "operator_audit_entry.py", source / "solve.py")
    for name in ("v4.py", "operator_core.py"):
        shutil.copyfile(SIDECAR / "candidate_1" / name, source / name)
    public_path = CONCEPT / "participant/input/examples/phonon_continuum_96.npz"
    with np.load(public_path, allow_pickle=False) as archive:
        instance = {key: archive[key] for key in archive.files}
    instance["n_freq"] = np.array(1031)
    instance["initial_delta"] = instance["initial_delta"][:, :1031].copy()
    tempfile.tempdir = str(SIDECAR / "scratch")
    sys.path.insert(0, str(CONCEPT / "evaluator"))
    import evaluate
    result, execution = evaluate.run_candidate(source, instance)
    labels = ("fused_even", "fused_odd", "prefix_modal_even", "prefix_modal_odd",
              "quadrature", "interpolation_nodes", "full_map_z", "full_map_delta")
    limits = (3e-12, 3e-12, 3e-7, 3e-7, 3e-12, 3e-12, 3e-12, 3e-12)
    values = result["delta"][0, :11] if result is not None else None
    checks = [{"name": label, "relative_error": float(value), "limit": limit, "passed": bool(value <= limit)}
              for label, value, limit in zip(labels, values[:8], limits)] if result is not None else []
    child = resource.getrusage(resource.RUSAGE_CHILDREN)
    parent_cpu = time.process_time() - STARTED
    child_cpu = child.ru_utime + child.ru_stime
    report = {
        **before,
        "audit": "Eight operator checks against the unfused mode-by-mode operator, including signed parity, finite-grid linear interpolation and Coulomb sum weights",
        "command": sys.executable + " -B " + str(Path(__file__).resolve()),
        "codepath": "Immutable active evaluate.run_candidate(operator_audit_submission, public_truncated_instance); no limit override",
        "not_an_inference_candidate": True,
        "not_an_achievability_claim": True,
        "public_input_sha256": digest(public_path),
        "test_truncation_n_freq": 1031,
        "operator_source_sha256": digest(source / "operator_core.py"),
        "source_solver_sha256": digest(source / "v4.py"),
        "execution": execution,
        "checks": checks,
        "passed": len(checks) == 8 and all(check["passed"] for check in checks),
        "warm_modal_rank": int(values[8]) if result is not None else None,
        "warm_frequencies": int(values[9]) if result is not None else None,
        "exact_symbol_bytes": int(values[10]) if result is not None else None,
        "identity_rechecked_after_run": identities() == before,
        "parent_cpu_seconds": parent_cpu,
        "children_cpu_seconds": child_cpu,
        "consumed_cpu_seconds": parent_cpu + child_cpu,
    }
    (SIDECAR / "operator_audit.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({key: report[key] for key in ("passed", "warm_modal_rank", "warm_frequencies", "consumed_cpu_seconds", "checks")}))


if __name__ == "__main__":
    main()
