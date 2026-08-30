"""Private sector ED using cached spin bases and sparse Kronecker sums."""

from functools import lru_cache
from itertools import combinations
import time

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigsh


@lru_cache(maxsize=None)
def spin_basis(n_sites, particles):
    states = np.array([sum(1 << site for site in occupied)
                       for occupied in combinations(range(n_sites), particles)], dtype=np.int64)
    occupations = ((states[:, None] >> np.arange(n_sites)) & 1).astype(np.float64)
    lookup = {int(state): index for index, state in enumerate(states)}
    transitions = []
    for first in range(n_sites):
        for second in range(first + 1, n_sites):
            sources, destinations, signs = [], [], []
            between = ((1 << second) - 1) ^ ((1 << (first + 1)) - 1)
            for source, state in enumerate(states):
                if ((state >> first) & 1) != ((state >> second) & 1):
                    sources.append(source)
                    destinations.append(lookup[int(state ^ (1 << first) ^ (1 << second))])
                    signs.append(-1.0 if (int(state & between).bit_count() % 2) else 1.0)
            transitions.append((first, second, np.array(destinations, dtype=np.int32),
                                np.array(sources, dtype=np.int32), np.array(signs)))
    return states, occupations, transitions


def spin_kinetic(hopping, particles):
    n_sites = len(hopping)
    states, occupations, transitions = spin_basis(n_sites, particles)
    rows, columns, values = [], [], []
    for first, second, destinations, sources, signs in transitions:
        if hopping[first, second] != 0:
            rows.append(destinations)
            columns.append(sources)
            values.append(-hopping[first, second] * signs)
    if not rows:
        return sparse.csr_matrix((len(states), len(states))), occupations
    return sparse.coo_matrix((np.concatenate(values),
                              (np.concatenate(rows), np.concatenate(columns))),
                             shape=(len(states), len(states))).tocsr(), occupations


def sector_matrix(hopping, interaction, potential, up_count, down_count):
    up_kinetic, up_occupation = spin_kinetic(hopping, up_count)
    down_kinetic, down_occupation = spin_kinetic(hopping, down_count)
    diagonal = ((up_occupation * interaction) @ down_occupation.T
                + (up_occupation @ potential)[:, None]
                + (down_occupation @ potential)[None, :]).ravel()
    matrix = (sparse.kron(up_kinetic, sparse.eye(len(down_occupation)), format="csr")
              + sparse.kron(sparse.eye(len(up_occupation)), down_kinetic, format="csr"))
    return matrix + sparse.diags(diagonal, format="csr")


def ground_state(matrix, seed=871, tolerance=2e-11, ncv=32):
    if matrix.shape[0] <= 32:
        energies, vectors = np.linalg.eigh(matrix.toarray())
        energy, vector = float(energies[0]), vectors[:, 0]
    else:
        initial = np.random.default_rng(seed).standard_normal(matrix.shape[0])
        energies, vectors = eigsh(matrix, k=1, which="SA", tol=tolerance,
                                  v0=initial, ncv=ncv, maxiter=12000)
        energy, vector = float(energies[0]), vectors[:, 0]
    residual = float(np.linalg.norm(matrix @ vector - energy * vector))
    if residual > 2e-8 or not np.isfinite(energy):
        raise RuntimeError(f"Unacceptable eigensolver residual: {residual}")
    return energy, residual, vector


def label_instance(hopping, interaction, potential, seed=871, tolerance=2e-11):
    start = time.perf_counter()
    cpu_start = time.process_time()
    half = len(hopping) // 2
    sectors = ((half, half), (half, half - 1), (half + 1, half), (half + 1, half - 1))
    energies, residuals = [], []
    for up_count, down_count in sectors:
        matrix = sector_matrix(hopping, interaction, potential, up_count, down_count)
        energy, residual, _ = ground_state(matrix, seed, tolerance)
        energies.append(energy)
        residuals.append(residual)
    gaps = np.array([energies[1] + energies[2] - 2.0 * energies[0],
                     energies[3] - energies[0]])
    if gaps[1] < -2e-8:
        raise RuntimeError(f"Spin-sector ordering violated: {gaps}")
    return {"gaps": gaps, "energies": np.array(energies),
            "residuals": np.array(residuals), "seconds": time.perf_counter() - start,
            "cpu_seconds": time.process_time() - cpu_start}
