"""Public signed-energy-error gradient and its two finite integral probes."""

import json
from pathlib import Path

import numpy as np

from oracle import DeterminantCC
from stencil import stencil_points

LIMITS = json.loads(Path(__file__).with_name("constraints.json").read_text())


def energy_error_gradient(pair_matrix, amplitudes, oracle=None):
    oracle = DeterminantCC() if oracle is None else oracle
    matrix = np.asarray(pair_matrix, dtype=float)
    amplitudes = np.asarray(amplitudes, dtype=float)
    if matrix.shape != (15, 15) or not np.all(np.isfinite(matrix)):
        raise ValueError("expected finite 15 by 15 pair matrix")
    if amplitudes.shape != (oracle.count,) or not np.all(np.isfinite(amplitudes)):
        raise ValueError("expected finite CCSD amplitude vector")
    hamiltonian, _, _ = oracle.hamiltonian(LIMITS["orbital_energies"], matrix)
    residual, jacobian, transformed, positive, inverse = oracle.equations(hamiltonian, amplitudes)
    if max(abs(residual)) > LIMITS["cc_residual_max"]:
        raise ValueError("adaptive gradient requires a stationary base root")
    energy_derivative = np.array([(transformed @ generator - generator @ transformed)
                                 [oracle.reference, oracle.reference] for generator in oracle.generators])
    multipliers = np.linalg.solve(jacobian.T, -energy_derivative)
    left_reference = oracle.ref.copy()
    left_reference[oracle.targets] = multipliers
    left = left_reference @ inverse
    right = positive @ oracle.ref
    _, vectors = np.linalg.eigh(hamiltonian)
    exact = vectors[:, 0]
    axes = []
    gradient = []
    for row in range(15):
        for column in range(row, 15):
            axis = np.zeros((15, 15))
            axis[row, column] = axis[column, row] = 1.0 if row == column else 1 / np.sqrt(2.0)
            derivative, _, _ = oracle.hamiltonian(np.zeros(6), axis)
            axes.append(axis)
            gradient.append(left @ derivative @ right - exact @ derivative @ exact)
    gradient = np.array(gradient)
    norm = float(np.linalg.norm(gradient))
    if not np.all(np.isfinite(gradient)) or not np.isfinite(norm):
        raise ValueError("nonfinite adaptive gradient")
    fallback = norm <= LIMITS["adaptive_gradient_zero_tolerance"]
    direction = axes[0].copy() if fallback else np.einsum("k,kij->ij", gradient / norm, axes)
    return {"coordinates": gradient.tolist(), "norm": norm, "direction": direction.tolist(),
            "zero_gradient_fallback": bool(fallback), "derivative": "signed_CCSD_minus_FCI_energy"}


def probe_points(pair_matrix, amplitudes, oracle=None):
    response = energy_error_gradient(pair_matrix, amplitudes, oracle)
    points = list(stencil_points(pair_matrix))
    direction = np.array(response["direction"])
    matrix = np.asarray(pair_matrix, dtype=float)
    for sign in (1, -1):
        metadata = {"point": len(points), "axis": None, "sign": sign, "kind": "energy_gradient"}
        points.append((metadata, matrix + sign * LIMITS["robust_stencil_radius"] * direction))
    return points, response
