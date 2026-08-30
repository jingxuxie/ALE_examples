"""Generation-three stencil, trusted coverage, security, and preservation audit."""

import hashlib
import json
import os
import sys
import time
from pathlib import Path

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import numpy as np

BASE = Path(__file__).resolve().parents[2]
OUTPUT = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE / "participant" / "workspace"))
sys.path.insert(0, str(BASE / "evaluator"))
sys.path.insert(0, str(BASE / "evaluator" / "hidden"))

from api import CONSTRAINTS, artifact, robust_screen
from audit import numerical_audit, parser_audit
from evaluate import evaluate_artifact, evaluate_data
from independent import IndependentSystem
from oracle import DeterminantCC
from robust import trusted_points
from stencil import STENCIL, stencil_points
from validate_oracle import validate


def main():
    started = time.monotonic()
    radius = CONSTRAINTS["robust_stencil_radius"]
    zero = np.zeros((15, 15))
    public = list(stencil_points(zero))
    trusted = trusted_points(zero, radius)
    metadata_match = all(left[0] == right[0] for left, right in zip(public, trusted))
    matrix_error = max(float(np.max(abs(left[1] - right[1]))) for left, right in zip(public, trusted))
    axes = np.array([point.ravel() / radius for metadata, point in public[1::2]])
    orthogonality_error = float(np.max(abs(axes @ axes.T - np.eye(120))))
    displacement_error = max(abs(np.linalg.norm(point) - radius) for metadata, point in public[1:])
    pairing_error = max(float(np.max(abs(public[index][1] + public[index + 1][1])))
                        for index in range(1, 241, 2))
    public_oracle = DeterminantCC()
    private_oracle = IndependentSystem()
    integral_errors = []
    for point_index in (1, 2, 3, 4, 119, 120, 239, 240):
        interaction = public[point_index][1]
        matrix = public_oracle.hamiltonian(CONSTRAINTS["orbital_energies"], interaction)[0]
        independent = private_oracle.build(np.array(CONSTRAINTS["orbital_energies"]), interaction)[0]
        integral_errors.append(float(np.max(abs(matrix - independent))))
    old_limits = json.loads((BASE / "adversary/generation_2_snapshot/participant/workspace/constraints.json").read_text())
    restored = dict(CONSTRAINTS)
    restored.pop("robust_stencil_radius")
    restored.pop("robust_stencil_points")
    restored["evaluator_timeout_seconds"] = old_limits["evaluator_timeout_seconds"]
    original_bounds_preserved = restored == old_limits
    zero_report = json.loads((OUTPUT / "zero_example_evaluation.json").read_text())
    zero_diagnostic = zero_report["diagnostics"]
    zero_coverage = (zero_diagnostic["admissible"] and not zero_report["passed"]
                     and zero_report["core_score"] == 0
                     and zero_diagnostic["stencil"]["path_certificates_evaluated"] == 241
                     and len(zero_diagnostic["points"]) == 241)
    aggregate_consistency = (zero_diagnostic["worst_population_violation_observed"]
                             == min(point["occupation_violation"] for point in zero_diagnostic["points"])
                             and zero_diagnostic["max_dad_observed"]
                             == max(point["rdm_dad"] for point in zero_diagnostic["points"]))
    boundary = np.zeros((15, 15))
    boundary[0, 0] = 1.5
    boundary_path = OUTPUT / "boundary_domain_case.json"
    boundary_path.write_text(json.dumps(artifact(boundary, np.zeros(18)), allow_nan=False))
    boundary_report = evaluate_artifact(boundary_path, OUTPUT)
    boundary_rejected = (not boundary_report["passed"] and boundary_report["reason"] == "stencil_domain_failure"
                         and boundary_report["diagnostics"]["physics_failure_claim"] is False)
    public_boundary = robust_screen(boundary, np.zeros(18), check_paths=False)
    public_domain_agrees = public_boundary["reason"] == "stencil_domain_failure"
    protected = json.loads((OUTPUT / "preservation_before.json").read_text())
    preserved = all(hashlib.sha256((BASE / name).read_bytes()).hexdigest() == digest
                    for name, digest in protected.items())
    old_rejections = []
    for label, relative in [("v_2", "champions/generation_2/submission.json"),
                            ("v_2_r2", "attempts/v_2_r2/submission.json")]:
        path = BASE / relative
        report = evaluate_artifact(path, path.parent)
        (OUTPUT / (label + "_generation_3_evaluation.json")).write_text(json.dumps(report, indent=2, allow_nan=False))
        base_report = evaluate_data(json.loads(path.read_text()), check_path=True)
        old_rejections.append({"label": label, "base_passes_original_screens": base_report["passed"],
                               "robust_passed": report["passed"], "reason": report["reason"],
                               "failure_clusters": report["diagnostics"].get("failure_clusters"),
                               "valid_points": report["diagnostics"].get("stencil", {}).get("evaluated_points"),
                               "passed": base_report["passed"] and not report["passed"]
                               and report["reason"] == "robust_constraints_failed"})
    report = {"stencil": {"point_count": len(public), "metadata_match": metadata_match,
                           "public_private_matrix_error": matrix_error, "axis_orthogonality_error": orthogonality_error,
                           "radius_error": float(displacement_error), "plus_minus_error": pairing_error,
                           "independent_integral_error": max(integral_errors)},
              "original_bounds_preserved": original_bounds_preserved,
              "private_public_constraints_match": CONSTRAINTS == json.loads((BASE / "evaluator/hidden/constraints.json").read_text()),
              "public_stencil_radius_match": radius == STENCIL["radius"] == 0.001,
              "zero_example_complete_certificates": zero_coverage,
              "zero_example_aggregate_consistency": aggregate_consistency,
              "domain_failure_not_physics_failure": boundary_rejected and public_domain_agrees,
              "old_champion_rejection": old_rejections, "historical_files_preserved": preserved,
              "oracle_sanity": validate(), "independent_numerics": numerical_audit(),
              "security": parser_audit(OUTPUT), "runtime_seconds": time.monotonic() - started}
    report["passed"] = (len(public) == len(trusted) == 241 and metadata_match and matrix_error < 1e-15
                        and orthogonality_error < 1e-14 and displacement_error < 1e-15 and pairing_error == 0
                        and max(integral_errors) < 1e-12 and original_bounds_preserved
                        and report["private_public_constraints_match"] and report["public_stencil_radius_match"]
                        and zero_coverage and aggregate_consistency and boundary_rejected and public_domain_agrees
                        and all(row["passed"] for row in old_rejections) and preserved
                        and report["oracle_sanity"]["passed"] and report["independent_numerics"]["passed"]
                        and report["security"]["passed"])
    (OUTPUT / "robust_audit.json").write_text(json.dumps(report, indent=2, allow_nan=False))
    print(json.dumps({"passed": report["passed"], "stencil": report["stencil"],
                      "complete_path_certificates": 241, "security_cases": report["security"]["case_count"],
                      "runtime_seconds": report["runtime_seconds"]}, indent=2), flush=True)
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
