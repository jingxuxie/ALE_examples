"""Independent pool certificate, prefix, fermionic sign and dense-expm checks."""

import copy
import hashlib
import itertools
import json
import math
import sys
import time
from functools import lru_cache

sys.dont_write_bytecode = True

import numpy as np
import scipy
from scipy.linalg import expm
from scipy.sparse import csr_matrix, eye, kron
from scipy.sparse.linalg import expm_multiply

from pool_api import (
    ROOT, MINIMUM_LATE_SPECTRUM_CHANGE, dense_entangled, engine, evaluate,
    load_cases, metrics, opposite_spin_double, save_assets, spin_layout,
)


@lru_cache(maxsize=4)
def independent_basis(n_orbitals, n_electrons):
    return tuple(sorted(sum(1 << orbital for orbital in occupied)
                        for occupied in itertools.combinations(range(n_orbitals), n_electrons)))


@lru_cache(maxsize=4)
def annihilators(n_orbitals):
    identity = eye(2, format="csr")
    parity = csr_matrix(np.diag([1.0, -1.0]))
    lowering = csr_matrix([[0.0, 1.0], [0.0, 0.0]])
    result = []
    for orbital in range(n_orbitals):
        operator = csr_matrix([[1.0]])
        for site in reversed(range(n_orbitals)):
            factor = parity if site < orbital else lowering if site == orbital else identity
            operator = kron(operator, factor, format="csr")
        result.append(operator)
    return tuple(result)


@lru_cache(maxsize=2048)
def independent_generator(n_orbitals, n_electrons, excitation):
    operators = annihilators(n_orbitals)
    operator = eye(1 << n_orbitals, format="csr")
    for orbital in excitation.create:
        operator = operator @ operators[orbital].T
    for orbital in reversed(excitation.annihilate):
        operator = operator @ operators[orbital]
    basis = np.asarray(independent_basis(n_orbitals, n_electrons))
    operator = operator[basis, :][:, basis]
    return (operator - operator.T).tocsr()


def check_sign_and_schmidt_conventions():
    operators = annihilators(4)
    anticommutation_tests = 0
    for left in range(4):
        for right in range(4):
            residual = operators[left] @ operators[right].T + operators[right].T @ operators[left]
            if left == right:
                residual = residual - eye(16, format="csr")
            assert residual.count_nonzero() == 0
            anticommutation_tests += 1
    random = np.random.default_rng(928174)
    product_tests, maximum_error = 0, 0.0
    for n_orbitals, n_electrons in ((10, 4), (10, 6), (12, 6)):
        indices, rows, columns, signs, dimension = spin_layout(n_orbitals, n_electrons)
        alpha, beta = random.normal(size=dimension), random.normal(size=dimension)
        alpha /= np.linalg.norm(alpha)
        beta /= np.linalg.norm(beta)
        product = np.outer(alpha, beta)
        state = np.zeros(len(independent_basis(n_orbitals, n_electrons)))
        state[indices] = signs * product[rows, columns]
        assert metrics(state, n_orbitals, n_electrons)["schmidt_rank"] == 1
        labels = engine.allowed_excitations(n_orbitals)
        local = []
        for rank, spin in itertools.product((1, 2), (0, 1)):
            matching = [label for label in labels if len(label.annihilate) == rank
                        and all(orbital % 2 == spin for orbital in label.annihilate + label.create)]
            local.extend((matching[0], matching[-1]))
        for excitation in local:
            theta = float(random.uniform(-1.1, 1.1))
            rotated = engine.apply_rotation(state, engine.rotation_pairs(n_orbitals, n_electrons, excitation), theta)
            independent = expm_multiply(theta * independent_generator(n_orbitals, n_electrons, excitation), state)
            maximum_error = max(maximum_error, float(np.max(abs(rotated - independent))))
            assert metrics(rotated, n_orbitals, n_electrons)["schmidt_rank"] == 1
            assert abs(metrics(rotated, n_orbitals, n_electrons)["effective_schmidt_rank"] - 1.0) < 1e-12
            state = rotated
            product_tests += 1
    assert maximum_error < 1e-12
    return {"pass": True, "anticommutation_tests": anticommutation_tests,
            "spin_local_product_state_tests": product_tests, "maximum_rotation_error": maximum_error}


def verify_case(case, gates, metadata):
    assert case.determinants == independent_basis(case.n_orbitals, case.n_electrons)
    assert len(gates) == case.max_gates == metadata["prefixes"][-1]["prefix_length"]
    assert len(set(label for label, theta in gates)) == len(gates)
    prefix_depth = metadata["dense_full_rank_prefix_depth"]
    assert prefix_depth == (16 if case.n_orbitals == 10 else 20)
    indices = spin_layout(case.n_orbitals, case.n_electrons)[0]
    state = engine.reference_state(case)
    independent = state.copy()
    previous_generator = None
    previous_metrics = metrics(state, case.n_orbitals, case.n_electrons)
    maximum_error, maximum_dense_error, minimum_step = 0.0, 0.0, math.inf
    minimum_suffix_amplitude, minimum_suffix_schmidt = math.inf, math.inf
    minimum_suffix_effective_rank_fraction, minimum_late_spectrum_change = math.inf, math.inf
    dense_tests, noncommuting_pairs, prefix_checks = 0, 0, 0
    for position, (excitation, theta) in enumerate(gates):
        assert 0.42 <= abs(theta) <= 1.20
        generator = independent_generator(case.n_orbitals, case.n_electrons, excitation)
        spin_generator = generator[indices, :][:, indices]
        if previous_generator is not None:
            commutator = previous_generator @ spin_generator - spin_generator @ previous_generator
            assert commutator.count_nonzero() > 0, (case.case_id, position, "commuting in physical spin sector")
            noncommuting_pairs += 1
        previous_generator = spin_generator
        old_state, old_independent = state, independent
        state = engine.apply_rotation(state, engine.rotation_pairs(case.n_orbitals, case.n_electrons, excitation), theta)
        independent = expm_multiply(theta * generator, independent)
        error = float(np.max(abs(state - independent)))
        maximum_error = max(maximum_error, error)
        assert error < 2e-12
        if position in (0, prefix_depth - 1, len(gates) - 1):
            dense_state = expm(theta * spin_generator.toarray()) @ old_independent[indices]
            dense_error = float(np.max(abs(dense_state - independent[indices])))
            maximum_dense_error = max(maximum_dense_error, dense_error)
            assert dense_error < 2e-12
            dense_tests += 1
        diagnostics = metrics(state, case.n_orbitals, case.n_electrons)
        saved = metadata["prefixes"][position + 1]
        for field in ("support", "schmidt_rank", "support_above_1e-8"):
            assert diagnostics[field] == saved[field]
        for field in ("minimum_absolute_amplitude", "minimum_schmidt_value", "effective_schmidt_rank", "participation_ratio"):
            assert abs(diagnostics[field] - saved[field]) < 2e-11
        assert np.allclose(diagnostics["schmidt_values"], saved["schmidt_values"], atol=1e-13, rtol=1e-12)
        step = float(np.linalg.norm(state - old_state))
        minimum_step = min(minimum_step, step)
        assert step >= 0.10
        spectrum_change = float(np.linalg.norm(np.asarray(diagnostics["schmidt_values"]) - previous_metrics["schmidt_values"]))
        if position + 1 >= prefix_depth:
            assert dense_entangled(diagnostics), (case.case_id, position, "prefix criteria")
            minimum_suffix_amplitude = min(minimum_suffix_amplitude, diagnostics["minimum_absolute_amplitude"])
            minimum_suffix_schmidt = min(minimum_suffix_schmidt, diagnostics["minimum_schmidt_value"])
            minimum_suffix_effective_rank_fraction = min(minimum_suffix_effective_rank_fraction,
                                                        diagnostics["effective_schmidt_rank"] / diagnostics["schmidt_dimension"])
        if position >= prefix_depth:
            assert opposite_spin_double(excitation)
            assert spectrum_change >= MINIMUM_LATE_SPECTRUM_CHANGE
            minimum_late_spectrum_change = min(minimum_late_spectrum_change, spectrum_change)
        previous_metrics = diagnostics
        prefix_checks += 1
    rotation_fidelity = engine.squared_overlap(case.target, state)
    independent_fidelity = engine.squared_overlap(case.target, independent)
    assert rotation_fidelity >= engine.FIDELITY_THRESHOLD and independent_fidelity >= engine.FIDELITY_THRESHOLD
    target_error = float(np.max(abs(independent - case.target)))
    assert target_error < 2e-12
    assert abs(float(independent @ independent) - 1.0) < engine.NORM_TOLERANCE
    return {"case_id": case.case_id, "pass": True, "n_orbitals": case.n_orbitals, "n_electrons": case.n_electrons,
            "gate_count": len(gates), "rotation_fidelity": rotation_fidelity, "independent_fidelity": independent_fidelity,
            "maximum_rotation_vs_independent_error": maximum_error, "maximum_target_error": target_error,
            "maximum_dense_expm_error": maximum_dense_error, "dense_expm_checks": dense_tests,
            "prefix_checks": prefix_checks, "noncommuting_adjacent_pairs": noncommuting_pairs,
            "dense_full_rank_prefix_depth": prefix_depth, "late_opposite_spin_double_count": len(gates) - prefix_depth,
            "minimum_state_step": minimum_step, "minimum_suffix_absolute_amplitude": minimum_suffix_amplitude,
            "minimum_suffix_schmidt_value": minimum_suffix_schmidt,
            "minimum_suffix_effective_rank_fraction": minimum_suffix_effective_rank_fraction,
            "minimum_late_spectrum_change": minimum_late_spectrum_change,
            "final_support": previous_metrics["support"], "final_schmidt_rank": previous_metrics["schmidt_rank"],
            "final_effective_schmidt_rank": previous_metrics["effective_schmidt_rank"]}


def check_constraints(submission, cases):
    probes = []
    for name in ("over_budget", "spin_flip", "boolean_angle", "missing_case", "unknown_key"):
        altered = copy.deepcopy(submission)
        if name == "over_budget":
            altered["circuits"][0]["gates"].append(altered["circuits"][0]["gates"][0])
        elif name == "spin_flip":
            altered["circuits"][0]["gates"][0] = {"annihilate": [0], "create": [1], "theta": 0.7}
        elif name == "boolean_angle":
            altered["circuits"][0]["gates"][0]["theta"] = True
        elif name == "missing_case":
            altered["circuits"].pop()
        else:
            altered["code"] = "not executable"
        try:
            engine.validate_submission(altered, cases)
        except engine.ValidationError:
            probes.append({"name": name, "pass": True})
        else:
            raise AssertionError("invalid submission accepted: " + name)
    return probes


def main():
    started = time.perf_counter()
    cases = load_cases(ROOT / "targets.json")
    submission = engine.read_json(ROOT / "certificates.json")
    gates = engine.validate_submission(submission, cases)
    metadata = json.loads((ROOT / "metadata.json").read_text())
    metadata_by_id = {record["case_id"]: record for record in metadata["cases"]}
    assert set(metadata_by_id) == {case.case_id for case in cases}
    conventions = check_sign_and_schmidt_conventions()
    checks = []
    for case in cases:
        result = verify_case(case, gates[case.case_id], metadata_by_id[case.case_id])
        individual = evaluate(ROOT / "cases" / case.case_id / "certificate.json",
                              ROOT / "cases" / case.case_id / "targets.json")
        assert individual["pass"] and individual["core"] == result["rotation_fidelity"]
        checks.append(result)
        print(json.dumps({"verified": case.case_id, "independent_fidelity": result["independent_fidelity"],
                          "maximum_error": result["maximum_target_error"]}), flush=True)
    witness = evaluate(ROOT / "certificates.json")
    assert witness["pass"]
    constraints = check_constraints(submission, cases)
    report = {"pass": True, "case_count": len(cases), "fidelity_threshold": engine.FIDELITY_THRESHOLD,
              "witness_core": witness["core"], "independent_worst_fidelity": min(result["independent_fidelity"] for result in checks),
              "maximum_target_error": max(result["maximum_target_error"] for result in checks),
              "total_gate_prefix_checks": sum(result["prefix_checks"] for result in checks),
              "dense_expm_checks": sum(result["dense_expm_checks"] for result in checks),
              "sign_and_schmidt_conventions": conventions, "constraint_probes": constraints,
              "independent_method": "Kronecker Jordan-Wigner generators, full fixed-N expm_multiply, spin-block dense scipy.linalg.expm",
              "cases": checks, "runtime_seconds": time.perf_counter() - started,
              "numpy_version": np.__version__, "scipy_version": scipy.__version__,
              "active_task_modified": False, "current_attempts_read": False, "contestant_algorithms_run": False}
    index = json.loads((ROOT / "index.json").read_text())
    index.update(status="verified_private_pool_ready", verification_path="verification.json", witness_score_path="witness_score.json")
    save_assets({"verification.json": report, "witness_score.json": witness, "index.json": index}, replace=True)
    manifest = {"confidential": True, "status": "verified_private_pool_ready", "case_count": len(cases),
                "fidelity_threshold": engine.FIDELITY_THRESHOLD, "sha256": {
                    str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                    for path in sorted(ROOT.rglob("*")) if path.is_file() and path.name != "manifest.json"
                    and "__pycache__" not in path.parts}}
    save_assets({"manifest.json": manifest}, replace=True)
    print(json.dumps({key: report[key] for key in ("pass", "case_count", "witness_core", "independent_worst_fidelity",
                                                  "maximum_target_error", "total_gate_prefix_checks", "dense_expm_checks", "runtime_seconds")}), flush=True)


if __name__ == "__main__":
    main()
