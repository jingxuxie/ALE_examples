"""Independent stationary response and exact finite-probe construction."""

import math

import numpy as np
from scipy.linalg import eigh, solve


def trusted_response(oracle, energies, interaction, amplitudes, zero_tolerance):
    hamiltonian, _, _ = oracle.build(energies, interaction)
    residual, jacobian, hbar, positive, negative = oracle.equations(hamiltonian, amplitudes)
    if np.max(np.abs(residual)) > 2e-9:
        raise ValueError("nonstationary adaptive base")
    derivatives = np.array([(hbar @ operator - operator @ hbar)[oracle.reference, oracle.reference]
                            for operator in oracle.generators])
    multipliers = solve(jacobian.T, -derivatives)
    bra = oracle.ref.copy()
    bra[oracle.targets] = multipliers
    left = bra @ negative
    right = positive @ oracle.ref
    _, states = eigh(hamiltonian)
    exact = states[:, 0]
    coefficients = []
    axes = []
    for row in range(15):
        for column in range(row, 15):
            direction = np.zeros((15, 15))
            direction[row, column] = 1.0 if row == column else math.sqrt(0.5)
            direction[column, row] = direction[row, column]
            derivative_hamiltonian, _, _ = oracle.build(np.zeros(6), direction)
            coefficient = float(left @ derivative_hamiltonian @ right - exact @ derivative_hamiltonian @ exact)
            coefficients.append(coefficient)
            axes.append(direction)
    magnitude = float(np.linalg.norm(coefficients))
    if not np.all(np.isfinite(coefficients)) or not math.isfinite(magnitude):
        raise ValueError("nonfinite independent energy response")
    fallback = magnitude <= zero_tolerance
    direction = axes[0].copy() if fallback else sum(coefficient * axis / magnitude
                                                  for coefficient, axis in zip(coefficients, axes))
    return {"coordinates": coefficients, "norm": magnitude, "direction": direction.tolist(),
            "zero_gradient_fallback": bool(fallback), "derivative": "signed_CCSD_minus_FCI_energy"}
