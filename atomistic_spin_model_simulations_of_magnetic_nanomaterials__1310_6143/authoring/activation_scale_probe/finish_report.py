import datetime
import hashlib
import json
import platform
import subprocess
from pathlib import Path

import numpy as np
import scipy

from reference import ROOT, TASK, TRUSTED, write_json


def main():
    references = {str(count): json.loads((ROOT / f"N{count}/validation.json").read_text()) for count in [40, 128, 512, 2048]}
    submissions = {str(count): json.loads((ROOT / f"N{count}/submission_result.json").read_text()) for count in [512, 2048]}
    bounded = json.loads((ROOT / "bounded_reference/N2048/validation.json").read_text())
    source = TASK / "authoring/spirit"
    revision = subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip()
    if subprocess.check_output(["git", "-C", str(source), "diff", "--name-only"], text=True).strip():
        raise RuntimeError("tracked native source is not clean")
    evidence = {
        "submission": TASK / "pilots/activation/attempt/solve.py",
        "trusted_case": TRUSTED / "case.json",
        "trusted_native_solution": TRUSTED / "solution.json",
        "trusted_input_wrapper": TASK / "pilots/activation/private/build_references.py",
        "shared_isolation_harness": TASK / "authoring/isolated.py",
        "native_library": source / "core/python/spirit/libSpirit.so",
        "native_sparse_htst": source / "core/src/engine/Sparse_HTST.cpp",
        "native_dense_htst": source / "core/src/engine/HTST.cpp",
        "native_gneb": source / "core/src/engine/Method_GNEB.cpp",
        "native_hamiltonian": source / "core/src/engine/Hamiltonian_Heisenberg.cpp",
    }
    hashes = {name: {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()} for name, path in evidence.items()}
    if hashes["submission"]["sha256"] != submissions["512"]["immutable_submission_sha256"] or hashes["submission"]["sha256"] != submissions["2048"]["immutable_submission_sha256"]:
        raise RuntimeError("submission is not unchanged")
    if any(record["trusted_seed_sha256"] != hashes["trusted_native_solution"]["sha256"] for record in references.values()):
        raise RuntimeError("trusted frozen seed changed")
    summary = {
        "result": "credible_source_scale_time_limit_counterexample",
        "counterexample_n_spins": 2048,
        "frozen_pilot_changed": False,
        "new_model_launches": 0,
        "source_revision": revision,
        "reference_resource_limit_confirmation": {"timeout_seconds": 90, "address_space_gib": 2, "gnu_time": (ROOT / "logs/bounded_reference.time").read_text().strip(), "native_validation": bounded},
        "submission_results": submissions,
        "reference_certification": references,
        "limitations": [
            "N=512/2048 extends the physical family's size, outside the frozen pilot's original N=6..40 range; this is not a retrospective grading failure.",
            "Native long-chain GNEB starts from a localized trusted N=40 saddle padded with uniform bulk; its measured time is not a cold global search.",
            "Three-image climbing GNEB confirms/refines the saddle, not a finely resolved whole transition path; full-chain native downhill branches certify the connection.",
            "No completed N=2048 submission output exists, so its numerical core accuracy at that size is unknown, not scored as numerically wrong.",
            "The observed failure is wall-time, not the 2-GiB memory limit. No internal solver profile was collected, so a specific eigensolver call is not conclusively blamed.",
            "Reference computational limits match 90 s/2 GiB but the trusted native reference is not run inside the submission's bubblewrap namespace; startup/cleanup overheads differ.",
            "Rare-event discussion uses classical T=0.5 K (barrier/kBT about 34.3); no quantum correction or experimental rate claim is made.",
            "No exhaustive global-lowest-saddle proof is supplied; this is a connected index-one boundary saddle independently matched by the cold submitted solver at N=512.",
        ],
    }
    write_json(ROOT / "result.json", summary)
    artifacts = {}
    for path in sorted(ROOT.rglob("*")):
        if path.is_file() and path.name != "provenance.json":
            artifacts[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    write_json(ROOT / "provenance.json", {"generated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "owned_scope": str(ROOT), "source_revision": revision,
                                         "python": platform.python_version(), "numpy": np.__version__, "scipy": scipy.__version__, "kernel": platform.release(),
                                         "threads": {"OPENBLAS_NUM_THREADS": 1, "OMP_NUM_THREADS": 1}, "read_only_input_hashes": hashes, "artifact_sha256": artifacts})
    print(json.dumps({"result": summary["result"], "source_2048_gnu_time": summary["reference_resource_limit_confirmation"]["gnu_time"],
                      "submission_512": submissions["512"]["resources"], "submission_2048": submissions["2048"]["resources"]}, indent=2), flush=True)


if __name__ == "__main__":
    main()
