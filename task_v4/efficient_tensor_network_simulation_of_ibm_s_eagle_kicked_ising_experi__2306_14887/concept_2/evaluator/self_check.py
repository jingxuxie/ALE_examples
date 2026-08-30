"""Independent exact evolution and contraction audits; not a contestant evaluator."""

import os
for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from scipy.linalg import expm

sys.path.insert(0, str(Path(__file__).resolve().parent / "resources"))
from simulator import exact_state, expand_mps, measure, mps_state, rx
import simulator
from protocol import waveforms
from reference import zz1


def independent_state(angles, n_sites=12):
    amplitudes = np.zeros(2 ** n_sites, dtype=complex)
    amplitudes[0] = 1
    indices = np.arange(len(amplitudes))
    for angle in angles:
        for site in range(n_sites):
            zero = indices[(indices & (1 << site)) == 0]
            one = zero | (1 << site)
            first, second = amplitudes[zero].copy(), amplitudes[one].copy()
            amplitudes[zero] = np.cos(angle / 2) * first - 1j * np.sin(angle / 2) * second
            amplitudes[one] = np.cos(angle / 2) * second - 1j * np.sin(angle / 2) * first
        for site in range(n_sites):
            opposite = ((indices >> site) ^ (indices >> ((site + 1) % n_sites))) & 1
            amplitudes *= np.where(opposite, np.exp(-1j * np.pi / 4), np.exp(1j * np.pi / 4))
    return amplitudes


def independent_magnetization(amplitudes):
    n_sites = int(np.log2(len(amplitudes)))
    total = 0.0
    for index, amplitude in enumerate(amplitudes):
        total += (n_sites - 2 * index.bit_count()) * abs(amplitude) ** 2 / n_sites
    return float(total / np.vdot(amplitudes, amplitudes).real)


def dense_state(angles, n_sites=4):
    identity = np.eye(2)
    pauli_x = np.array([[0, 1], [1, 0]])
    pauli_z = np.diag([1, -1])
    operators_x, operators_z = [], []
    for site in range(n_sites):
        product_x, product_z = np.array([[1]]), np.array([[1]])
        for other in range(n_sites):
            product_x = np.kron(product_x, pauli_x if site == other else identity)
            product_z = np.kron(product_z, pauli_z if site == other else identity)
        operators_x.append(product_x)
        operators_z.append(product_z)
    field = sum(operators_x)
    coupling = sum(operators_z[site] @ operators_z[(site + 1) % n_sites] for site in range(n_sites))
    entangler = expm(1j * np.pi / 4 * coupling)
    state = np.eye(2 ** n_sites, dtype=complex)[:, 0]
    for angle in angles:
        state = entangler @ expm(-1j * angle / 2 * field) @ state
    return state


def contracted_magnetization(tensors):
    total = 0.0
    for measured in range(len(tensors)):
        environment = np.ones((1, 1), dtype=complex)
        for site, tensor in enumerate(tensors):
            diagonal = np.array([1, -1]) if site == measured else np.ones(2)
            environment = np.einsum("ab,asr,bst,s->rt", environment, tensor.conj(), tensor, diagonal,
                                    optimize=True)
        total += environment.item().real / len(tensors)
    return total


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--witness", type=Path)
    options = parser.parse_args()
    random = np.random.default_rng(14887)
    checks = []
    def check(name, error, tolerance=2e-10):
        checks.append({"name": name, "error": float(error), "tolerance": tolerance,
                       "passed": bool(error < tolerance)})
        print(name, error, flush=True)
    for name, angles in [("zero", [0.0] * 8), ("clifford", [np.pi / 2] * 12),
                         ("random", random.uniform(0.1, 1.47, 14))]:
        exact = exact_state(angles)
        reference = independent_state(angles)
        check(name + "_independent_state", np.linalg.norm(exact - reference))
        check(name + "_unit_norm", abs(np.linalg.norm(exact) - 1))
        approximation, diagnostics = mps_state(angles, 64)
        fidelity_error = max(0.0, 1 - abs(np.vdot(exact, approximation)) ** 2)
        check(name + "_chi64_infidelity", fidelity_error)
        phase = np.vdot(exact, approximation)
        check(name + "_chi64_state", np.linalg.norm(approximation - phase / abs(phase) * exact))
        check(name + "_chi64_discarded", diagnostics["discarded_sum"])
        check(name + "_independent_observable", abs(measure(exact)["magnetization"] - independent_magnetization(reference)))
        check(name + "_independent_zz1", abs(measure(exact)["zz1"] - zz1(reference)))
    for angle in (0, 0.371, np.pi / 2):
        check("rx_unitary_" + str(angle), np.linalg.norm(rx(angle).conj().T @ rx(angle) - np.eye(2)))
    angles = [0.34, 1.17, 0.92, 0.61, 1.22]
    check("independent_dense_hamiltonian", np.linalg.norm(exact_state(angles, 4) - dense_state(angles)))
    tensors, diagnostics = mps_state(angles * 3, 8, return_tensors=True)
    check("mps_transfer_observable", abs(contracted_magnetization(tensors) - measure(expand_mps(tensors))["magnetization"]))
    check("zero_magnetization_one", abs(measure(exact_state([0] * 8))["magnetization"] - 1))
    check("one_layer_cosine", abs(measure(exact_state([0.713]))["magnetization"] - np.cos(0.713)))
    original = simulator.svd
    def alternate_svd(*args, **kwargs):
        kwargs["lapack_driver"] = "gesdd"
        return original(*args, **kwargs)
    driver_angles = random.uniform(0.2, 1.4, 16)
    for chi in (4, 8, 16):
        first = mps_state(driver_angles, chi)[0]
        simulator.svd = alternate_svd
        second = mps_state(driver_angles, chi)[0]
        simulator.svd = original
        overlap = np.vdot(first, second)
        check("svd_driver_state_chi" + str(chi), np.linalg.norm(second - overlap / abs(overlap) * first), 2e-8)
    if options.witness:
        witness = json.loads(options.witness.read_text())
        spec = json.loads((Path(__file__).resolve().parent / "resources" / "target.json").read_text())
        for family, angles in waveforms(witness, spec).items():
            selected_corners = {"corner_00/nominal", "corner_21/tilt_minus", "corner_42/offset_plus", "corner_63/nominal"}
            if "/" in family and family not in selected_corners:
                continue
            reference = independent_state(angles)
            check("witness_" + family + "_independent_state", np.linalg.norm(exact_state(angles) - reference))
            full_rank = mps_state(angles, 64)[0]
            overlap = np.vdot(reference, full_rank)
            check("witness_" + family + "_chi64", np.linalg.norm(full_rank - overlap / abs(overlap) * reference), 2e-8)
            for chi in (4, 8, 16):
                first = mps_state(angles, chi)[0]
                simulator.svd = alternate_svd
                second = mps_state(angles, chi)[0]
                simulator.svd = original
                check("witness_" + family + "_driver_" + str(chi), abs(zz1(first) - zz1(second)), 2e-8)
    report = {"passed": all(item["passed"] for item in checks), "checks": checks,
              "numpy": np.__version__}
    options.output.write_text(json.dumps(report, indent=2) + "\n")
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
