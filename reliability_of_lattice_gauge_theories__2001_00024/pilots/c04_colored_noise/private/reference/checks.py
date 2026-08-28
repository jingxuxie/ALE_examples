import json
import os
from pathlib import Path
import time

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"

import numpy as np
from scipy.linalg import expm

from build_cases import make_case
from engine import (audit_response, build_model, calibration_rates, channels, fit_bath,
                    hamiltonian, propagate, raw_generator, secular_generator, spectrum)


def check_all():
    started = time.perf_counter()
    checks = {}

    def record(name, error, tolerance):
        checks[name] = dict(error=float(error), tolerance=float(tolerance), passed=bool(error <= tolerance))
        if error > tolerance:
            raise AssertionError(f"{name}: {error} > {tolerance}")

    case = make_case("brown_degenerate", 2, 91827, "validation")["case"]
    operators = build_model(case)
    record("hamiltonian_hermiticity", np.linalg.norm(operators["hzero"] - operators["hzero"].conj().T), 1e-12)
    record("gauss_commutators", max(np.linalg.norm(operators["hzero"] @ charge - charge @ operators["hzero"])
                                     for charge in operators["charges"]), 1e-12)
    record("initial_gauss_sector", np.linalg.norm(operators["gauge"] @ operators["initial"]), 1e-12)
    number = sum(operators["occupancies"])
    record("intended_number_conservation", np.linalg.norm(operators["hzero"] @ number - number @ operators["hzero"]), 1e-12)
    hsystem = hamiltonian(case, operators, case["audit"]["action"])
    bath = case["audit"]["bath"]
    channel_matrices = channels(case, operators, bath["eta"])
    compiled = secular_generator(hsystem, channel_matrices, bath)
    identity_vector = np.eye(64).ravel(order="F")
    record("trace_preserving", np.linalg.norm(identity_vector @ compiled["generator"]), 1e-10)
    record("even_spectrum_unital", np.linalg.norm(compiled["dissipator"] @ identity_vector), 1e-10)
    _, densities = propagate(case, operators, compiled, return_states=True)
    record("evolved_trace", np.max(np.abs(np.trace(densities, axis1=1, axis2=2) - 1)), 1e-10)
    record("evolved_hermiticity", max(np.linalg.norm(density - density.conj().T) for density in densities), 1e-10)
    record("evolved_positivity", max(0, -min(np.linalg.eigvalsh(density).min() for density in densities)), 1e-10)
    random = np.random.default_rng(915)
    rotated = compiled["vectors"].astype(complex).copy()
    for group in compiled["energy_groups"]:
        unitary, _ = np.linalg.qr(random.normal(size=(len(group), len(group)))
                                  + 1j * random.normal(size=(len(group), len(group))))
        rotated[:, group] = rotated[:, group] @ unitary
    rotated_model = secular_generator(hsystem, channel_matrices, bath,
                                      eigensystem=(compiled["energies"], rotated))
    original_audit = audit_response(compiled, case["audit"]["states"])
    rotated_audit = audit_response(rotated_model, case["audit"]["states"])
    record("degenerate_projector_rotation_invariance", max(
        np.linalg.norm(np.asarray(first[part]) - np.asarray(second[part]))
        for first, second in zip(original_audit, rotated_audit) for part in ("real", "imag", "activity")), 1e-10)

    identity = np.eye(2)
    flip = np.array([[0, 1], [1, 0]])
    pauliz = np.diag([1, -1])
    white = dict(beta=0, amplitude=0.037, cutoff=1.0, floor=0.0, eta=0.0)
    single = secular_generator(0.7 * pauliz, [flip], white)
    initial = single["vectors"].conj().T @ np.diag([1, 0]) @ single["vectors"]
    evolved = (expm(single["generator"].toarray() * 2.3) @ initial.ravel(order="F")).reshape((2, 2), order="F")
    evolved = single["vectors"] @ evolved @ single["vectors"].conj().T
    record("single_spin_white_flip_rate", abs(evolved[1, 1] - (1 - np.exp(-2 * white["amplitude"] * 2.3)) / 2), 1e-12)
    two_hamiltonian = 0.6 * (np.kron(pauliz, identity) + np.kron(identity, pauliz))
    collective = np.kron(flip, identity) + np.kron(identity, flip)
    two = secular_generator(two_hamiltonian, [collective], white)
    antisymmetric = np.array([0, 1, -1, 0]) / np.sqrt(2)
    dark = two["vectors"].conj().T @ np.outer(antisymmetric, antisymmetric) @ two["vectors"]
    record("collective_dark_state", np.linalg.norm(two["dissipator"] @ dark.ravel(order="F")), 1e-12)
    split = secular_generator(two_hamiltonian, [collective], white, split_transitions=True)
    record("rank_one_jump_ablation_detected", float(np.linalg.norm(split["dissipator"] @ dark.ravel(order="F")) < 0.02), 0)
    lowering = np.array([[0, 1], [0, 0]])
    jump_up = np.kron(lowering, identity) + np.kron(identity, lowering)
    explicit = np.zeros((16, 16), dtype=complex)
    for jump in (jump_up, jump_up.T):
        product = jump.conj().T @ jump
        explicit += white["amplitude"] * (np.kron(jump.conj(), jump)
                     - 0.5 * np.kron(np.eye(4), product) - 0.5 * np.kron(product.T, np.eye(4)))
    explicit -= 1j * (np.kron(np.eye(4), two_hamiltonian) - np.kron(two_hamiltonian.T, np.eye(4)))
    transform = np.kron(two["vectors"].conj(), two["vectors"])
    physical = transform @ two["generator"].toarray() @ transform.conj().T
    record("independent_two_spin_explicit_jumps", np.linalg.norm(explicit - physical), 1e-12)
    record("independent_exponential_dynamics", np.linalg.norm(expm(explicit * 1.7) - expm(physical * 1.7)), 1e-12)
    zero = secular_generator(np.zeros((2, 2)), [flip], white)
    raw = raw_generator(np.zeros((2, 2)), [flip], white["amplitude"])
    record("zero_frequency_lindblad_limit", np.linalg.norm((zero["generator"] - raw["generator"]).toarray()), 1e-12)
    for beta in (0, 1, 2):
        true = dict(beta=beta, amplitude=0.014, cutoff=0.4 if beta else 1,
                    floor=0.001 if beta else 0, eta=0.63)
        rows = []
        for center in np.geomspace(0.03, 20, 12):
            for mode in (0, 1, -1):
                row = dict(omega=[center * 0.8, center, center * 1.2], weight=[0.25, 0.5, 0.25], mode=mode)
                mean = float(calibration_rates(true, [row])[0])
                row.update(value=mean, sigma=max(1e-7, 0.01 * mean))
                rows.append(row)
        fitted = fit_bath(rows)
        record(f"noiseless_calibration_beta_{beta}", float(fitted["beta"] != beta), 0)
        frequencies = np.geomspace(0.01, 30, 20)
        record(f"noiseless_spectrum_beta_{beta}", np.max(np.abs(spectrum(fitted, frequencies)
                                                               / spectrum(true, frequencies) - 1)), 1e-6)
    report = dict(passed=True, checks=checks, elapsed_seconds=time.perf_counter() - started,
                  scope="Independent analytic/explicit-jump limits and 64-dimensional invariants, not official author validation")
    target = Path(__file__).resolve().parents[1] / "validation/analytical_checks.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    check_all()
