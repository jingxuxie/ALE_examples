import os

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import argparse
import functools
import json
from pathlib import Path

import numpy as np
from scipy.linalg import eigh
from scipy.sparse import csr_matrix, diags, eye, kron
from scipy.sparse.linalg import eigsh


TARGETS = ("odd_gap", "even_gap", "odd_spacing")
LOCAL_STATES = 16
OSCILLATOR_STATES = 80
OSCILLATOR_FREQUENCY = 2.0


@functools.lru_cache(maxsize=1)
def oscillator_operators():
    size = OSCILLATOR_STATES
    frequency = OSCILLATOR_FREQUENCY
    numbers = np.arange(size + 4)
    position = np.diag(np.sqrt(numbers[1:] / (2.0 * frequency)), 1)
    position += position.T
    squared = position @ position
    fourth = squared @ squared
    kinetic = np.diag(frequency * (numbers + 0.5)) - frequency**2 * squared / 2.0
    return tuple(operator[:size, :size] for operator in (position, squared, fourth, kinetic))


def local_basis(mass):
    position, squared, fourth, kinetic = oscillator_operators()
    hamiltonian = kinetic + mass * squared / 2.0 + fourth / 4.0
    levels = np.empty(LOCAL_STATES)
    vectors = np.zeros((OSCILLATOR_STATES, LOCAL_STATES))
    for parity in (0, 1):
        energies, states = eigh(
            hamiltonian[parity::2, parity::2],
            subset_by_index=(0, LOCAL_STATES // 2 - 1),
            check_finite=False,
        )
        levels[parity::2] = energies
        vectors[parity::2, parity::2] = states
    projected = vectors.T @ position @ vectors
    projected[np.abs(projected) < 1e-15] = 0.0
    return levels, csr_matrix(projected)


@functools.lru_cache(maxsize=2)
def parity_indices(sites):
    numbers = np.indices((LOCAL_STATES,) * sites).reshape(sites, -1)
    parity = np.sum(numbers, axis=0) % 2
    return tuple(np.flatnonzero(parity == value) for value in (0, 1))


def dimensionless_gaps(mass, coupling, sites):
    edge_levels, edge_position = local_basis(mass + coupling)
    if sites == 2:
        diagonal = (edge_levels[:, None] + edge_levels[None, :]).ravel()
        interaction = kron(edge_position, edge_position, format="csr")
    else:
        middle_levels, middle_position = local_basis(mass + 2.0 * coupling)
        diagonal = (
            edge_levels[:, None, None]
            + middle_levels[None, :, None]
            + edge_levels[None, None, :]
        ).ravel()
        identity = eye(LOCAL_STATES, format="csr")
        interaction = kron(
            kron(edge_position, middle_position, format="csr"), identity, format="csr"
        ) + kron(
            identity, kron(middle_position, edge_position, format="csr"), format="csr"
        )
    hamiltonian = (diags(diagonal) - coupling * interaction).tocsr()
    sector_energies = []
    for indices in parity_indices(sites):
        sector = hamiltonian[indices][:, indices]
        initial = np.sin(np.arange(len(indices)) + 0.123)
        energies = eigsh(
            sector,
            k=2,
            which="SA",
            tol=1e-12,
            v0=initial,
            return_eigenvectors=False,
        )
        sector_energies.append(np.sort(energies))
    even, odd = sector_energies
    return np.array((odd[0] - even[0], even[1] - even[0], odd[1] - odd[0]))


def predict(cases):
    predictions = []
    for case in cases:
        scale = (case["lambda"] / 6.0) ** (1.0 / 3.0)
        mass = case["mu2"] / scale**2
        coupling = case["kappa"] / scale**2
        gaps = scale * dimensionless_gaps(mass, coupling, case["sites"])
        if not np.all(np.isfinite(gaps)) or not np.all(gaps > 0.0):
            raise ArithmeticError("Nonpositive or nonfinite spectral gap")
        predictions.append({"id": case["id"], "targets": dict(zip(TARGETS, gaps.tolist()))})
    return {"schema_version": 1, "predictions": predictions}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--train", required=True)
    parser.add_argument("--output", required=True)
    arguments = parser.parse_args()
    cases = json.loads(Path(arguments.input).read_text())["cases"]
    result = predict(cases)
    Path(arguments.output).write_text(json.dumps(result, allow_nan=False) + "\n")


if __name__ == "__main__":
    main()
