import math

import numpy as np
from scipy import sparse


NODES, WEIGHTS = np.polynomial.legendre.leggauss(64)
NODES = (NODES + 1) / 2
WEIGHTS = WEIGHTS / 2


def integrals(cutoff, mass, reference, shifts):
    shifts = np.asarray(shifts)
    lower = np.maximum(cutoff, shifts + 5 * mass)
    energies = lower[..., None] / NODES
    reduced = energies - shifts[..., None]
    logarithm = np.log(reduced / mass)
    base = WEIGHTS * lower[..., None] / (NODES**2 * (energies - reference) * reduced**2)
    return -np.stack((np.sum(base / (2 * math.pi), axis=-1),
                     np.sum(base * 3 * logarithm / (4 * math.pi**2), axis=-1),
                     np.sum(base * (3 * logarithm**2 / (4 * math.pi**3) - 1 / (16 * math.pi)), axis=-1)), axis=-1)


def local_matrix(operators, coefficients, cutoff, mass, reference):
    weights = integrals(cutoff, mass, reference, 0.0)
    result = sparse.csr_matrix(next(iter(operators.values())).shape)
    for key, vector in coefficients.items():
        if key in operators:
            result = result + float(vector @ weights) * operators[key]
    return result


def state_correction(operators, coefficients, energies, vector, cutoff, mass, eigenvalue, local_reference):
    grid = np.linspace(0.0, cutoff, 241)
    tabulated = integrals(cutoff, mass, eigenvalue, grid)
    local = integrals(cutoff, mass, local_reference, 0.0)
    correction = 0.0
    for key, factors in coefficients.items():
        if key not in operators:
            continue
        operator = operators[key].tocoo()
        shifts = (energies[operator.row] + energies[operator.col]) / 2
        changes = np.interp(shifts, grid, tabulated @ factors) - float(local @ factors)
        correction += np.sum(vector[operator.row] * vector[operator.col] * operator.data * changes)
    return float(correction)
