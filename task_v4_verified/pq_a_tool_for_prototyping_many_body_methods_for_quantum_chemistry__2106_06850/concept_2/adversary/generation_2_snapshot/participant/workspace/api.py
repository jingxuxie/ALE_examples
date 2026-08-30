"""Public artifact interface and inexpensive endpoint screening."""

import json
from pathlib import Path

import numpy as np

from oracle import DeterminantCC

CONSTRAINTS = json.loads(Path(__file__).with_name("constraints.json").read_text())


def artifact(pair_matrix, amplitudes):
    return {"schema_version": 1, "orbital_energies": CONSTRAINTS["orbital_energies"],
            "pair_matrix": np.asarray(pair_matrix).tolist(),
            "amplitudes": np.asarray(amplitudes).tolist()}


def endpoint_failures(diagnostics):
    bounds = [
        ("cc_residual", "cc_residual_max", False),
        ("lambda_residual", "lambda_residual_max", False),
        ("energy_error", "energy_error_max", False),
        ("ground_overlap", "ground_overlap_min", True),
        ("reference_weight", "reference_weight_min", True),
        ("fci_gap", "fci_gap_min", True),
        ("hf_real_min", "hf_curvature_min", True),
        ("hf_imaginary_min", "hf_curvature_min", True),
        ("jacobian_condition", "jacobian_condition_max", False),
        ("lambda_norm", "lambda_norm_max", False),
        ("rdm_dad", "rdm_dad_max", False),
        ("amplitude_norm", "amplitude_norm_max", False),
    ]
    failures = []
    for key, bound, lower in bounds:
        value = diagnostics[key]
        if not np.isfinite(value) or (value < CONSTRAINTS[bound] if lower else value > CONSTRAINTS[bound]):
            failures.append(key)
    if min(diagnostics["eom_real"]) < CONSTRAINTS["eom_real_min"]:
        failures.append("eom_real_min")
    return failures


def screen(pair_matrix, initial=None, oracle=None):
    oracle = DeterminantCC() if oracle is None else oracle
    pair_matrix = np.asarray(pair_matrix, dtype=float)
    if pair_matrix.shape != (15, 15) or not np.all(np.isfinite(pair_matrix)):
        raise ValueError("pair_matrix must be a finite 15 by 15 array")
    if np.max(np.abs(pair_matrix - pair_matrix.T)) > CONSTRAINTS["symmetry_tolerance"]:
        raise ValueError("pair_matrix must be symmetric")
    if np.max(np.abs(pair_matrix)) > CONSTRAINTS["pair_entry_max"]:
        raise ValueError("pair entry bound exceeded")
    if np.linalg.norm(pair_matrix) > CONSTRAINTS["pair_frobenius_max"]:
        raise ValueError("pair Frobenius bound exceeded")
    hamiltonian, _, _ = oracle.hamiltonian(CONSTRAINTS["orbital_energies"], pair_matrix)
    result = oracle.solve(hamiltonian, initial)
    if not result.converged:
        return {"endpoint_feasible": False, "failures": ["cc_convergence"]}, result
    diagnostics = oracle.diagnostics(hamiltonian, result)
    failures = endpoint_failures(diagnostics)
    diagnostics["endpoint_feasible"] = not failures
    diagnostics["failures"] = failures
    diagnostics["target_reached"] = diagnostics["occupation_violation"] >= CONSTRAINTS["population_violation_min"]
    return diagnostics, result


def check_continuation(pair_matrix, amplitudes, oracle=None):
    oracle = DeterminantCC() if oracle is None else oracle
    previous = np.zeros(oracle.count)
    history = []
    for coupling in np.linspace(0, 1, CONSTRAINTS["continuation_steps"] + 1):
        hamiltonian, _, _ = oracle.hamiltonian(CONSTRAINTS["orbital_energies"], coupling * np.asarray(pair_matrix))
        result = oracle.solve(hamiltonian, previous, tolerance=2e-11, max_evaluations=250)
        if not result.converged or result.residual > CONSTRAINTS["cc_residual_max"]:
            return {"passed": False, "reason": "continuation_convergence", "history": history}
        exact_energies, exact_vectors = np.linalg.eigh(hamiltonian)
        right = result.right
        history.append({"coupling": float(coupling), "residual": result.residual,
                        "gap": float(exact_energies[1] - exact_energies[0]),
                        "overlap": float((exact_vectors[:, 0] @ right) ** 2 / (right @ right)),
                        "amplitude_step": float(np.linalg.norm(result.amplitudes - previous)),
                        "jacobian_singular_min": float(np.linalg.svd(result.jacobian, compute_uv=False)[-1])})
        previous = result.amplitudes
    endpoint_error = float(np.max(np.abs(previous - np.asarray(amplitudes))))
    passed = (min(row["gap"] for row in history) >= CONSTRAINTS["path_gap_min"]
              and min(row["overlap"] for row in history) >= CONSTRAINTS["path_overlap_min"]
              and max(row["amplitude_step"] for row in history) <= CONSTRAINTS["path_amplitude_step_max"]
              and min(row["jacobian_singular_min"] for row in history) >= CONSTRAINTS["path_jacobian_singular_min"]
              and endpoint_error <= CONSTRAINTS["path_endpoint_tolerance"])
    return {"passed": bool(passed), "endpoint_error": endpoint_error, "history": history}
