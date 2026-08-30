"""Author-side cross-checks; no candidate data are required."""

import json
import sys
from pathlib import Path

import numpy as np
from scipy.linalg import eigh, expm

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "participant" / "workspace"))
from oracle import DeterminantCC, random_pair_matrix


def validate():
    rng = np.random.default_rng(314159)
    oracle = DeterminantCC(6, 2)
    energies = np.array([-1.2, -0.6, 0.6, 0.9, 1.3, 1.6])
    interaction = random_pair_matrix(rng, 0.08)
    hamiltonian, one_body, tensor = oracle.hamiltonian(energies, interaction)
    result, _ = oracle.continuation(energies, interaction)
    exact_values, exact_vectors = eigh(hamiltonian)
    multipliers, left, stationarity = oracle.lambda_state(result)
    density = oracle.rdm(left, result.right)
    exact_density = oracle.rdm(exact_vectors[:, 0], exact_vectors[:, 0])
    checks = {"n2_ccsd_fci_energy_error": abs(result.energy - exact_values[0]),
              "n2_ccsd_fci_rdm_error": float(np.max(np.abs(density - exact_density))),
              "n2_eom_fci_error": float(np.max(np.abs(np.sort(np.linalg.eigvals(result.jacobian).real)
                                                              - (exact_values[1:] - exact_values[0])))),
              "n2_lambda_residual": stationarity}
    oracle = DeterminantCC()
    energies = np.array([-1.2, -0.9, -0.5, 0.5, 0.9, 1.2])
    interaction = random_pair_matrix(rng, 0.17)
    hamiltonian, one_body, tensor = oracle.hamiltonian(energies, interaction)
    result, _ = oracle.continuation(energies, interaction)
    multipliers, left, stationarity = oracle.lambda_state(result)
    density = oracle.rdm(left, result.right)
    direction = rng.normal(size=result.amplitudes.shape)
    direction /= np.linalg.norm(direction)
    step = 1e-5
    residual_plus = oracle.equations(hamiltonian, result.amplitudes + step * direction)[0]
    residual_minus = oracle.equations(hamiltonian, result.amplitudes - step * direction)[0]
    checks["jacobian_finite_difference_error"] = float(np.max(np.abs(
        (residual_plus - residual_minus) / (2 * step) - result.jacobian @ direction)))
    perturbation = rng.normal(size=(6, 6))
    perturbation = (perturbation + perturbation.T) / 2
    operator = (perturbation.ravel() @ oracle.one_flat).reshape(oracle.size, oracle.size)
    plus = oracle.solve(hamiltonian + step * operator, result.amplitudes)
    minus = oracle.solve(hamiltonian - step * operator, result.amplitudes)
    checks["lambda_energy_derivative_error"] = float(abs((plus.energy - minus.energy) / (2 * step)
                                                       - np.sum(perturbation * density)))
    positive, negative = oracle.exponentials(result.amplitudes)
    cluster = (result.amplitudes @ oracle.generator_flat).reshape(oracle.size, oracle.size)
    checks["nilpotent_exponential_error"] = float(np.max(np.abs(expm(cluster) - positive)))
    checks["inverse_exponential_error"] = float(np.max(np.abs(negative @ positive - oracle.identity)))
    fock = one_body + sum(tensor[:, occupied, :, occupied] for occupied in range(3))
    checks["canonical_fock_error"] = float(np.max(np.abs(fock - np.diag(energies))))
    real_hessian, imaginary_hessian = oracle.hf_stability(hamiltonian)
    direction = rng.normal(size=len(oracle.singles))
    direction /= np.linalg.norm(direction)
    excitation = np.einsum("k,kij->ij", direction, oracle.singles)
    step = 1e-4
    for label, generator, hessian in [("real", excitation - excitation.T, real_hessian),
                                      ("imaginary", 1j * (excitation + excitation.T), imaginary_hessian)]:
        plus = expm(step * generator) @ oracle.ref
        minus = expm(-step * generator) @ oracle.ref
        difference = ((plus.conj() @ hamiltonian @ plus + minus.conj() @ hamiltonian @ minus
                       - 2 * (oracle.ref @ hamiltonian @ oracle.ref)) / step ** 2).real
        checks[label + "_hf_hessian_error"] = float(abs(difference - direction @ hessian @ direction))
    exact_values, exact_vectors = eigh(hamiltonian)
    exact_density = oracle.rdm(exact_vectors[:, 0], exact_vectors[:, 0])
    occupations = eigh(exact_density, eigvals_only=True)
    checks["exact_rdm_hermiticity_error"] = float(np.max(np.abs(exact_density - exact_density.T)))
    checks["exact_rdm_trace_error"] = float(abs(np.trace(exact_density) - 3))
    checks["exact_rdm_positivity_violation"] = float(max(0, -occupations[0], occupations[-1] - 1))
    checks["passed"] = all(value < (2e-6 if "hessian" in key else 2e-7) for key, value in checks.items())
    return checks


if __name__ == "__main__":
    result = validate()
    print(json.dumps(result, indent=2, allow_nan=False))
    raise SystemExit(0 if result["passed"] else 1)
