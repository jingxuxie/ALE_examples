"""Snapshot private candidates and invoke the unchanged isolated artifact scorer."""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import numpy as np

PACKET = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKET / "participant" / "workspace"))
from oracle import DeterminantCC
from api import CONSTRAINTS, artifact


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--final", action="store_true")
    arguments = parser.parse_args()
    started = time.monotonic()
    suffix = "_final" if arguments.final else ""
    output = PACKET / "authoring" / ("certified_portfolio" + suffix)
    output.mkdir(exist_ok=True)
    oracle = DeterminantCC()
    records = []
    sources = [("finite_author", "finite_author_soft/candidate.json"),
               ("finite_v3", "finite_v3_soft/candidate.json"),
               ("reduced_gen1", "reduced_gen1/last_iterate.json"),
               ("reduced_r2", "reduced_r2/candidate.json"),
               ("joint_author", "joint_finite_author/candidate.json"),
               ("joint_v3", "joint_finite_v3/candidate.json")]
    if arguments.final:
        sources = [("joint_scaled_author_retained", "joint_scaled_author/candidate.json"),
                   ("joint_scaled_v3_retained", "joint_scaled_v3/candidate.json")] + sources
        sources += [("joint_scaled_author", "joint_scaled_author/last_iterate.json"),
                    ("joint_scaled_v3", "joint_scaled_v3/last_iterate.json"),
                    ("known_gen3_private_seed", PACKET.parents[1] / "adversary/generation_3/private_centered_candidate.json")]
    for label, relative in sources:
        source = Path(relative)
        if not source.is_absolute():
            source = PACKET / "authoring" / source
        if not source.exists():
            continue
        data = json.loads(source.read_text())
        matrix = np.array(data["pair_matrix"])
        hamiltonian = oracle.hamiltonian(CONSTRAINTS["orbital_energies"], matrix)[0]
        solution = oracle.solve(hamiltonian, np.array(data["amplitudes"]), tolerance=2e-12, max_evaluations=300)
        candidate = output / (label + "_submission.json")
        candidate.write_text(json.dumps(artifact(matrix, solution.amplitudes), indent=2, allow_nan=False))
        report_path = output / (label + "_evaluation.json")
        command = [sys.executable, "-I", str(PACKET / "evaluator" / "evaluate.py"), str(candidate),
                   "--submission-dir", str(output), "--output", str(report_path)]
        process = subprocess.run(command, capture_output=True, text=True, timeout=930, check=False)
        (output / (label + "_evaluation.log")).write_text(process.stdout + process.stderr)
        report = json.loads(report_path.read_text())
        diagnostic = report.get("diagnostics", {})
        record = {"label": label, "source": str(relative), "sha256": hashlib.sha256(candidate.read_bytes()).hexdigest(),
                  "passed": report["passed"], "core_score": report["core_score"], "reason": report["reason"],
                  "runtime_seconds": report["runtime_seconds"], "worst": report.get("worst"),
                  "worst_population_observed": diagnostic.get("worst_population_violation_observed"),
                  "max_energy_error_observed": diagnostic.get("max_energy_error_observed"),
                  "max_dad_observed": diagnostic.get("max_dad_observed"),
                  "failure_clusters": diagnostic.get("failure_clusters"), "coverage": diagnostic.get("stencil")}
        records.append(record)
        print(json.dumps(record), flush=True)
        if report["passed"]:
            (PACKET / "authoring" / "privileged_witness_found.json").write_text(json.dumps(record, indent=2))
            break
    summary = {"privileged_witness_found": any(record["passed"] for record in records), "records": records,
               "runtime_seconds": time.monotonic() - started, "main_status_not_modified": True}
    (PACKET / "authoring" / ("portfolio_certification" + suffix + ".json")).write_text(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
