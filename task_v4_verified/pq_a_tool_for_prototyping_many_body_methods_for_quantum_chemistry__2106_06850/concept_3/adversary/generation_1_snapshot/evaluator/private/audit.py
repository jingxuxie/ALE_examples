"""Independent Jordan-Wigner construction and dense scipy.linalg.expm audit."""

import json
from pathlib import Path
import sys
import time

import numpy as np
from scipy.linalg import expm
from scipy.sparse import csr_matrix, eye, kron

from engine import (
    Excitation, allowed_excitations, apply_rotation, determinant_basis,
    load_cases, read_json, reference_state, rotation_pairs, squared_overlap,
    validate_submission,
)


PRIVATE = Path(__file__).resolve().parent


def annihilators(n_orbitals):
    identity = eye(2, format="csr")
    parity = csr_matrix(np.diag([1.0, -1.0]))
    lowering = csr_matrix([[0.0, 1.0], [0.0, 0.0]])
    result = []
    for orbital in range(n_orbitals):
        matrix = csr_matrix([[1.0]])
        for site in reversed(range(n_orbitals)):
            factor = parity if site < orbital else lowering if site == orbital else identity
            matrix = kron(matrix, factor, format="csr")
        result.append(matrix)
    return result


def dense_generator(operators, determinants, excitation):
    operator = eye(operators[0].shape[0], format="csr")
    for orbital in excitation.create:
        operator = operator @ operators[orbital].T
    for orbital in reversed(excitation.annihilate):
        operator = operator @ operators[orbital]
    indices = np.asarray(determinants)
    projected = operator[indices, :][:, indices].toarray()
    return projected - projected.T


def audit():
    started = time.perf_counter()
    random = np.random.default_rng(712)
    maximum_error = 0.0
    small_tests = 0
    anticommutation_error = 0.0
    for n_orbitals, n_electrons in ((4, 2), (6, 3)):
        operators = annihilators(n_orbitals)
        determinants = determinant_basis(n_orbitals, n_electrons)
        for left in range(n_orbitals):
            for right in range(n_orbitals):
                residual = operators[left] @ operators[right].T + operators[right].T @ operators[left]
                if left == right:
                    residual = residual - eye(1 << n_orbitals, format="csr")
                if residual.nnz:
                    anticommutation_error = max(anticommutation_error, float(abs(residual.data).max()))
        state = random.normal(size=len(determinants)) + 1j * random.normal(size=len(determinants))
        state /= np.linalg.norm(state)
        for excitation in allowed_excitations(n_orbitals):
            generator = dense_generator(operators, determinants, excitation)
            for theta in (-0.83, 0.31, 1.08):
                dense = expm(theta * generator) @ state
                rotated = apply_rotation(state, rotation_pairs(n_orbitals, n_electrons, excitation), theta)
                maximum_error = max(maximum_error, float(np.max(abs(dense - rotated))))
                small_tests += 1
    cases = load_cases(PRIVATE / "targets.json")
    certificates = validate_submission(read_json(PRIVATE / "certificates.json"), cases)
    certificate_results = []
    for case in cases:
        operators = annihilators(case.n_orbitals)
        dense_state, rotated_state = reference_state(case), reference_state(case)
        previous_generator = None
        noncommuting = 0
        step_error = 0.0
        for excitation, theta in certificates[case.case_id]:
            generator = dense_generator(operators, case.determinants, excitation)
            if previous_generator is not None:
                noncommuting += bool(np.any(previous_generator @ generator - generator @ previous_generator))
            previous_generator = generator
            dense_state = expm(theta * generator) @ dense_state
            rotated_state = apply_rotation(rotated_state, rotation_pairs(case.n_orbitals, case.n_electrons, excitation), theta)
            step_error = max(step_error, float(np.max(abs(dense_state - rotated_state))))
        fidelity = squared_overlap(case.target, dense_state)
        target_error = float(np.max(abs(dense_state - case.target)))
        certificate_results.append({
            "case_id": case.case_id, "dense_fidelity": fidelity,
            "maximum_step_error": step_error, "maximum_target_error": target_error,
            "noncommuting_adjacent_pairs": noncommuting,
            "gate_count": len(certificates[case.case_id]),
            "pass": fidelity >= 0.999999999 and step_error < 1e-12 and target_error < 1e-12
                    and noncommuting == len(certificates[case.case_id]) - 1,
        })
    passed = anticommutation_error == 0 and maximum_error < 1e-12 and all(entry["pass"] for entry in certificate_results)
    return {"pass": passed, "method": "independent sparse Kronecker Jordan-Wigner generators; dense scipy.linalg.expm",
            "small_rotation_tests": small_tests, "maximum_small_rotation_error": maximum_error,
            "anticommutation_error": anticommutation_error, "certificates": certificate_results,
            "runtime_seconds": time.perf_counter() - started,
            "numpy_version": np.__version__}


if __name__ == "__main__":
    report = audit()
    (PRIVATE / "audit.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, allow_nan=False))
    raise SystemExit(0 if report["pass"] else 1)
