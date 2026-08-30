import os

for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[variable] = '1'

import functools
import time

import numpy as np
from scipy.linalg import eigh
from scipy.sparse import csr_matrix, diags, eye, kron
from scipy.sparse.linalg import eigsh


@functools.lru_cache(None)
def oscillator(size=80, omega=2.0):
    indices = np.arange(size + 4)
    position = np.diag(np.sqrt(indices[1:] / (2 * omega)), 1)
    position += position.T
    squared = position @ position
    fourth = squared @ squared
    kinetic = np.diag(omega * (indices + 0.5)) - omega**2 * squared / 2
    return position[:size, :size], squared[:size, :size], fourth[:size, :size], kinetic[:size, :size]


def local_basis(mass, count, size=80):
    position, squared, fourth, kinetic = oscillator(size)
    hamiltonian = kinetic + mass * squared / 2 + fourth / 4
    levels = np.empty(count)
    vectors = np.zeros((size, count))
    for parity in (0, 1):
        values, states = eigh(hamiltonian[parity::2, parity::2], subset_by_index=(0, count // 2 - 1))
        levels[parity::2] = values
        vectors[parity::2, parity::2] = states
    projected = vectors.T @ position @ vectors
    projected[np.abs(projected) < 1e-15] = 0
    return levels, csr_matrix(projected)


@functools.lru_cache(None)
def parity_indices(count, sites):
    numbers = np.indices((count,) * sites).reshape(sites, -1)
    parity = np.sum(numbers, axis=0) % 2
    return [np.flatnonzero(parity == value) for value in (0, 1)]


def solve(mass, coupling, sites, count=12, tolerance=1e-12, return_levels=False):
    edge_levels, edge_position = local_basis(mass + coupling, count)
    identity = eye(count, format='csr')
    if sites == 2:
        diagonal = (edge_levels[:, None] + edge_levels[None, :]).ravel()
        hamiltonian = diags(diagonal) - coupling * kron(edge_position, edge_position, format='csr')
    else:
        middle_levels, middle_position = local_basis(mass + 2 * coupling, count)
        diagonal = (edge_levels[:, None, None] + middle_levels[None, :, None]
                    + edge_levels[None, None, :]).ravel()
        bond = kron(edge_position, middle_position, format='csr')
        hamiltonian = diags(diagonal) - coupling * (
            kron(bond, identity, format='csr')
            + kron(identity, kron(middle_position, edge_position, format='csr'), format='csr'))
    sectors = []
    for indices in parity_indices(count, sites):
        sector = hamiltonian.tocsr()[indices][:, indices]
        initial = np.sin(np.arange(len(indices)) + 0.123)
        energies = eigsh(sector, k=2, which='SA', tol=tolerance, v0=initial, return_eigenvectors=False)
        sectors.append(np.sort(energies))
    even, odd = sectors
    if return_levels:
        return np.array(sectors)
    return np.array([odd[0] - even[0], even[1] - even[0], odd[1] - odd[0]])


if __name__ == '__main__':
    for sites in (2, 3):
        for mass, coupling in ((3.5, 1.0), (0.0, 0.5), (-2.5, 0.5), (-4.2, 1.0)):
            for count in (8, 10, 12, 14, 16):
                start = time.process_time()
                gaps = solve(mass, coupling, sites, count)
                print(sites, mass, coupling, count, gaps, time.process_time() - start, flush=True)
