import os

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"

import json
import shutil
import sys
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "participant" / "workspace"))
sys.path.insert(0, str(ROOT / "evaluator"))
from evaluate import evaluate
from physics import EliashbergSolver, json_write, load_instance, read_artifact


def main():
    hidden = ROOT / "evaluator" / "hidden"
    instance = load_instance()
    baseline = json.loads((ROOT / "attempts" / "baseline_result.json").read_text())
    if not (baseline["admissible"] and baseline["score"] == 1.0 and not baseline["valid"]
            and baseline["converged"] and baseline["independent_audit_passed"]):
        raise RuntimeError("baseline validation failed")
    result = evaluate(hidden / "witness.npz", hidden / "witness_result.json", hidden / "witness_audit.json")
    if not result["valid"]:
        raise RuntimeError("private witness failed final verification: " + str(result))
    kernels = read_artifact(hidden / "witness.npz", instance["config"])
    total_rows = instance["row_sums"].sum(axis=0)
    scale = np.sqrt(instance["weights"] / (1 + total_rows))
    static_eigenvalues = [np.linalg.eigvalsh(modes.sum(axis=0) * np.outer(scale, scale)).tolist() for modes in kernels]
    solver = EliashbergSolver(instance["weights"], instance["row_sums"], instance["energies_mev"], instance["config"])
    audit = json.loads((hidden / "witness_audit.json").read_text())
    nominal = next(family for family in audit["physics"]["families"] if family["name"] == "nominal")
    fine = next(grid for grid in nominal["grids"] if grid["positive_count"] == 192)
    diagnostics = []
    for index, modes in enumerate(kernels):
        details = solver.eigenpair(modes, fine["transitions"][index]["tc_kelvin"], 192, gradient=True)
        gap = details["gap"][:, 0]
        singular_ratios = []
        for matrix in modes:
            singular = np.linalg.svd(matrix, compute_uv=False)
            singular_ratios.append(float(singular[3] / singular[0]))
        commutator = max(
            np.linalg.norm(modes[first] @ modes[second] - modes[second] @ modes[first])
            / (np.linalg.norm(modes[first]) * np.linalg.norm(modes[second]))
            for first in range(3) for second in range(first + 1, 3)
        )
        diagnostics.append({
            "kernel_index": index, "gap_participation": float(np.sum(gap ** 2) ** 2 / np.sum(gap ** 4)),
            "mode_sigma4_over_sigma1": singular_ratios, "maximum_normalized_commutator": float(commutator),
        })
    json_write(hidden / "witness_diagnostics.json", {
        "static_normalized_spectra": static_eigenvalues,
        "static_spectrum_max_difference": float(np.max(np.abs(np.array(static_eigenvalues)[0] - np.array(static_eigenvalues)[1]))),
        "kernels": diagnostics,
    })
    for destination in (ROOT / "champions", ROOT / "attempts" / "champions"):
        destination.mkdir(parents=True, exist_ok=True)
        for source_name, target_name in (("witness.npz", "curator_witness.npz"), ("witness_result.json", "curator_result.json"), ("witness_audit.json", "curator_audit.json")):
            shutil.copyfile(hidden / source_name, destination / target_name)
    adversary = json.loads((ROOT / "attempts" / "adversary" / "validation.json").read_text())
    if not adversary["passed"]:
        raise RuntimeError("artifact validation probes failed")
    json_write(ROOT / "adversary" / "validation.json", adversary)
    summary = json.loads((hidden / "search_summary.json").read_text())
    summary["independently_verified"] = True
    summary["final_score"] = result["score"]
    json_write(hidden / "search_summary.json", summary)
    json_write(ROOT / "status.json", {
        "schema_version": 1, "concept": "concept_2", "status": "ready",
        "ready_for_initial_attempts": True, "target_frozen": True,
        "target_ratio": instance["config"]["target_ratio"], "input_sha256": instance["input_sha256"],
        "fresh_runner_launched": False, "evaluation_mode": "artifact_only", "participant_artifact": "witness.npz",
        "baseline": {key: baseline[key] for key in ("score", "admissible", "valid", "converged", "independent_audit_passed")},
        "private_witness": {key: result[key] for key in ("score", "admissible", "valid", "converged", "independent_audit_passed")},
        "private_result": "evaluator/hidden/witness_result.json", "private_audit": "evaluator/hidden/witness_audit.json",
        "search_cpu_seconds": summary["cpu_seconds"], "search_restarts": summary["restarts"],
        "adversarial_probes_passed": len(adversary["probes"]),
    })
    print(json.dumps({"ready": True, "baseline": baseline, "private": result, "search": summary}, indent=2), flush=True)


if __name__ == "__main__":
    main()
