import datetime
import hashlib
import json
import os
from pathlib import Path
import sys
import time

sys.dont_write_bytecode = True
for variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "BLIS_NUM_THREADS"):
    os.environ[variable] = "1"

import numpy as np
from scipy.linalg import expm

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evaluator"))
sys.path.insert(0, str(ROOT / "participant" / "workspace"))
from evaluate import evaluate, fidelity_report, load_locked_problem, propagate
from build_instance import assemble_bits
from simulate import load_problem, score


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def main():
    started = time.monotonic()
    specification, model, drifts, controls, initial, targets = load_locked_problem()
    hidden = ROOT / "evaluator" / "hidden"
    public = ROOT / "participant" / "input"
    cases_directory = ROOT / "adversary" / "checker_cases"
    cases_directory.mkdir(exist_ok=True)
    names = [member["name"] for member in model["calibrations"]]
    checks = {}
    for filename in ("model.json", "spec.json", "targets.npz"):
        assert (public / filename).read_bytes() == (hidden / filename).read_bytes(), filename
    checks["all_target_constraints_public"] = True
    basis, bit_drifts, bit_controls, bit_initial = assemble_bits(model)
    matrix_error = max(float(np.max(abs(bit_drifts - drifts))), float(np.max(abs(bit_controls - controls))), float(np.max(abs(bit_initial - initial))))
    with np.load(public / "hamiltonians.npz", allow_pickle=False) as archive:
        matrix_error = max(matrix_error, float(np.max(abs(archive["drifts"] - drifts))), float(np.max(abs(archive["controls"] - controls))))
        assert np.array_equal(archive["basis"], basis)
        assert np.array_equal(archive["initial"], initial)
    assert len(basis) == 70 and matrix_error < 2e-14
    checks["tensor_vs_bit_matrix_max_error"] = matrix_error
    checks["target_orthonormality_error"] = max(float(np.linalg.norm(target.conj().T @ target - np.eye(6), ord=2)) for target in targets)
    checks["control_pair_commutator_norms"] = [float(np.linalg.norm(controls[first] @ controls[second] - controls[second] @ controls[first])) for first in range(3) for second in range(first + 1, 3)]
    assert min(checks["control_pair_commutator_norms"]) > 1
    witness = json.loads((hidden / "witness.json").read_text())
    amplitudes = np.array(witness["amplitudes"])
    independent = []
    for drift in drifts:
        states = initial.copy()
        for row in amplitudes:
            states = expm(-1j * specification["slice_duration"] * (drift + np.einsum("c,cij->ij", row, controls))) @ states
        independent.append(states)
    independent = np.array(independent)
    eigenstates = propagate(amplitudes, specification, drifts, controls, initial)
    checks["expm_vs_eigensystem_state_max_error"] = float(np.max(abs(independent - eigenstates)))
    checks["independent_expm_vs_public_target_max_error"] = float(np.max(abs(independent - targets)))
    assert checks["expm_vs_eigensystem_state_max_error"] < 1e-11
    assert checks["independent_expm_vs_public_target_max_error"] < 1e-12
    witness_report = evaluate(hidden / "witness.json")
    assert witness_report["passed"] and witness_report["evaluator_valid"]
    public_report = score(amplitudes, load_problem(public))
    assert public_report["passed"]
    checks["public_private_score_max_difference"] = max(abs(witness_report[key] - public_report[key]) for key in ("core_score", "worst_family_score", "minimum_column_fidelity"))
    assert checks["public_private_score_max_difference"] < 1e-11
    write_json(ROOT / "adversary" / "witness_report.json", witness_report)
    global_actual = targets * np.exp(1j * np.array([0.2, -1.7, 2.3, -0.9]))[:, None, None]
    global_report = fidelity_report(global_actual, targets, names)
    assert global_report["worst_family_score"] > 1 - 1e-11
    relative_actual = targets.copy()
    relative_actual[:, :, 0] *= -1
    relative_report = fidelity_report(relative_actual, targets, names)
    assert relative_report["minimum_column_fidelity"] > 1 - 1e-11
    assert relative_report["worst_family_score"] < 1e-12
    assert relative_report["core_score"] < 0.45
    checks["global_phase_invariance"] = global_report["worst_family_score"]
    checks["relative_phase_counterexample"] = relative_report
    malformed = {}
    for name, value in (("nan", float("nan")), ("positive_infinity", float("inf")), ("negative_infinity", -float("inf")), ("boolean", True), ("numeric_string", "0.0"), ("huge_finite", 1e308), ("huge_integer", 10 ** 500)):
        rows = np.zeros((24, 3)).tolist()
        rows[3][1] = value
        malformed[name] = json.dumps({"schema_version": 1, "amplitudes": rows})
    zero_payload = {"schema_version": 1, "amplitudes": np.zeros((24, 3)).tolist()}
    malformed["wrong_shape"] = json.dumps({"schema_version": 1, "amplitudes": [[0, 0, 0]]})
    malformed["boolean_version"] = json.dumps({"schema_version": True, "amplitudes": zero_payload["amplitudes"]})
    malformed["duplicate_key"] = '{"schema_version": 1, "schema_version": 1, "amplitudes": ' + json.dumps(zero_payload["amplitudes"]) + '}'
    malformed["extra_key"] = json.dumps(dict(zero_payload, controls=[]))
    malformed["oversized"] = " " * 65537 + "{}"
    malformed["invalid_json"] = "{"
    corruptions = {}
    for name, text in malformed.items():
        path = cases_directory / (name + ".json")
        path.write_text(text)
        report = evaluate(path)
        assert not report["valid"] and not report["passed"] and report["evaluator_valid"], (name, report)
        json.dumps(report, allow_nan=False)
        corruptions[name] = report["reason"]
    limits = np.array(specification["amplitude_limits"])
    physical = {}
    changed = np.zeros((24, 3))
    changed[10, 0] = limits[0] + 0.01
    physical["amplitude"] = (changed, "amplitude")
    changed = np.zeros((24, 3))
    changed[10, 0], changed[11, 0] = 0.6 * limits[0], -0.6 * limits[0]
    physical["adjacent_slew"] = (changed, "slew")
    changed = np.zeros((24, 3))
    changed[0, 0] = 0.96
    physical["zero_endpoint"] = (changed, "endpoint")
    physical["exposure"] = (np.tile([0.75, 0.60, 0.5], (24, 1)), "exposure")
    for name, (changed, expected) in physical.items():
        path = cases_directory / (name + ".json")
        write_json(path, {"schema_version": 1, "amplitudes": changed.tolist()})
        report = evaluate(path)
        assert not report["valid"] and report["evaluator_valid"] and expected in report["reason"], (name, report)
        corruptions[name] = report["reason"]
    checks["invalid_artifact_cases_rejected"] = corruptions
    checks["invalid_artifact_case_count"] = len(corruptions)
    for name, changed in (("nearby_witness", amplitudes + 1e-6 * np.sin(np.arange(72)).reshape(24, 3)), ("time_reversed", amplitudes[::-1])):
        path = cases_directory / (name + ".json")
        write_json(path, {"schema_version": 1, "amplitudes": changed.tolist()})
        report = evaluate(path)
        assert report["valid"] and report["evaluator_valid"]
        assert report["passed"] == (name == "nearby_witness"), (name, report)
        checks[name] = {key: report[key] for key in ("core_score", "worst_family_score", "passed")}
    baseline_report = evaluate(ROOT / "adversary" / "baseline_submission")
    assert baseline_report["valid"] and baseline_report["evaluator_valid"] and not baseline_report["passed"]
    write_json(ROOT / "adversary" / "baseline_evaluation.json", baseline_report)
    checks["validation_passed"] = True
    checks["elapsed_seconds"] = time.monotonic() - started
    write_json(ROOT / "adversary" / "validation_report.json", checks)
    public_manifest = {str(path.relative_to(ROOT / "participant")): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted((ROOT / "participant").rglob("*")) if path.is_file()}
    write_json(hidden / "public_manifest.json", public_manifest)
    status = {
        "concept": "concept_2",
        "name": "Calibration-aware coherent many-body pulse compilation",
        "verification_mode": "C_WITNESS_DESIGN_CONSTRUCTION",
        "status": "ready_for_fresh_tournament",
        "hardness_status": None,
        "empirical_hardness_decision": "Pending parent-run fresh attempts; weak baseline failure alone is not a hardness decision",
        "solvability": "demonstrated_by_privileged_witness",
        "classification_if_fresh_agents_fail": "hard_verified_achievable",
        "fixed_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "fixed_targets": {key: specification[key] for key in ("mean_isometry_fidelity_min", "worst_superposition_fidelity_min", "minimum_column_fidelity_min")},
        "public_ensemble_members": 4,
        "initial_register_dimension": 6,
        "hilbert_dimension": 70,
        "pulse_parameters": 72,
        "hidden_validation_physics": False,
        "baseline": {"submission": "adversary/baseline_submission/pulse.json", "report": "adversary/baseline_evaluation.json", "scores": baseline_report},
        "privileged_witness": {"submission": "evaluator/hidden/witness.json", "report": "adversary/witness_report.json", "scores": witness_report},
        "evaluator_validation": {"report": "adversary/validation_report.json", "passed": True, "corruption_cases": len(corruptions)},
        "fresh_attempts": [],
        "fresh_attempts_planned_by_parent": 2,
        "fresh_model": "ultima-alpha",
        "fresh_limit_seconds": 3600,
        "champions": [],
        "ratchet_generations": 0,
        "champion_counterexample_search": "Not run; no fresh champion exists",
        "artifact_interface": "pulse.json; solve.py optional",
        "isolation": "Expose only participant/ and an empty attempts/v_N; withhold evaluator/, adversary/, other attempts, champions, authoring sources and status",
        "difficulty_rationale": "A single long-duration bounded pulse must reproduce phase-coherent action on six register states for four interacting frustrated drifts. Noncommuting controls, fixed timing and joint slew/exposure constraints couple all 72 parameters; separate state fits or calibration-specific pulses are insufficient. This is a difficulty hypothesis pending the fresh tournament."
    }
    write_json(ROOT / "status.json", status)
    print(json.dumps({"ready": True, "baseline_core": baseline_report["core_score"], "baseline_worst": baseline_report["worst_family_score"], "witness_core": witness_report["core_score"], "witness_worst": witness_report["worst_family_score"], "corruptions_rejected": len(corruptions), "expm_eigensystem_error": checks["expm_vs_eigensystem_state_max_error"], "validation_seconds": checks["elapsed_seconds"]}, indent=2))


if __name__ == "__main__":
    main()
