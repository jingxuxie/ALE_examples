import time

import numpy as np
from scipy import linalg

from generated import restrict
from numerics import diagonalize, hamiltonian
from tails import tail_matrix


def extrapolate(cutoffs, energies, exponent=3.0):
    cutoffs = np.asarray(cutoffs)
    design = np.column_stack((np.ones(len(cutoffs)), (cutoffs[-1] / cutoffs) ** exponent))
    weights = (cutoffs / cutoffs[-1]) ** 3
    fit = np.linalg.lstsq(design * weights[:, None], energies * weights[:, None], rcond=None)[0]
    return fit[0]


def refined_levels(basis, maximum, coefficients, constant, terms, spectral, sample_step=0.5,
                   count_vectors=12, minimum=None, direct=True):
    started = time.perf_counter()
    base = hamiltonian(basis, coefficients, constant)
    matrix = base + tail_matrix(basis, maximum, terms, spectral, variant='local')
    values, eigenvectors, residual = diagonalize(matrix, 3 if direct else count_vectors, True)
    raw = diagonalize(base, 3)
    minimum = minimum or maximum - 8
    cutoffs = np.arange(minimum, maximum + sample_step / 2, sample_step)
    energies = []
    samples = []
    for cutoff in cutoffs:
        if abs(cutoff - maximum) < 1e-8:
            selected = values[:3]
        else:
            smaller = restrict(basis, cutoff)
            truncated = hamiltonian(smaller, coefficients, constant)
            truncated += tail_matrix(smaller, cutoff, terms, spectral, variant='local')
            if direct:
                selected = diagonalize(truncated)
            else:
                vectors = eigenvectors[:len(smaller['energy'])]
                reduced = vectors.T @ (truncated @ vectors)
                metric = vectors.T @ vectors
                selected = linalg.eigh(reduced, metric, eigvals_only=True, subset_by_index=(0, 2))
        energies.append(selected)
        samples.append({'internal_cutoff': float(cutoff), 'energies': selected.tolist()})
    energies = np.array(energies)
    prediction = extrapolate(cutoffs, energies)
    shifted = extrapolate(cutoffs[4:], energies[4:])
    exponent_low = extrapolate(cutoffs, energies, 2.5)
    exponent_high = extrapolate(cutoffs, energies, 3.5)
    uncertainty = np.maximum.reduce([abs(prediction - shifted), abs(prediction - exponent_low),
                                     abs(prediction - exponent_high), np.full(3, 0.0005)])
    ritz_error = 0.0
    if not direct:
        midpoint = float(cutoffs[len(cutoffs) // 2])
        check_basis = restrict(basis, midpoint)
        check_matrix = hamiltonian(check_basis, coefficients, constant)
        check_matrix += tail_matrix(check_basis, midpoint, terms, spectral, variant='local')
        exact_check = diagonalize(check_matrix)
        ritz_error = np.max(abs(exact_check - energies[len(cutoffs) // 2]))
    return {'levels': prediction.tolist(), 'raw': raw.tolist(), 'local': values[:3].tolist(),
            'samples': samples, 'uncertainty': uncertainty.tolist(), 'ritz_error': float(ritz_error),
            'residual': float(residual), 'seconds': time.perf_counter() - started}
