import argparse
import itertools
import json
import os
import time
from pathlib import Path

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import numpy as np
from scipy.linalg import eigh
from scipy.optimize import least_squares


PAIR_ENERGY = np.array([-1.20, -1.05, -0.90, 0.35, 0.45, 0.58, 0.72, 0.87, 1.03, 1.20])
VIRTUAL_COUNT = 7
EDGE_PAIRS = list(itertools.combinations(range(10), 2))
VIRTUAL_EDGES = list(itertools.combinations(range(3, 10), 2))
ORBITAL_EDGES = list(itertools.product(range(3), range(3, 10)))
TRIPLE_MASKS = [mask for mask in range(128) if mask.bit_count() == 3]
LOW_MASKS = [mask for mask in range(128) if mask.bit_count() <= 3]


def topology(mask):
    orbitals = [0, 1, 2] + [3 + index for index in range(7) if mask & (1 << index)]
    basis = list(itertools.combinations(orbitals, 3))
    occupation = np.zeros((len(basis), 10))
    for index, state in enumerate(basis):
        occupation[index, list(state)] = 1.0
    left, right, source, destination = [], [], [], []
    for row, state in enumerate(basis):
        for column in range(row):
            removed = set(state) - set(basis[column])
            added = set(basis[column]) - set(state)
            if len(removed) == 1:
                left.append(row)
                right.append(column)
                source.append(next(iter(removed)))
                destination.append(next(iter(added)))
    return occupation, np.array(left, int), np.array(right, int), np.array(source, int), np.array(destination, int)


TOPOLOGIES = {mask: topology(mask) for mask in LOW_MASKS + [127]}


def decode(parameters):
    hopping = np.zeros((10, 10))
    density = np.zeros((10, 10))
    for index, (source, destination) in enumerate(ORBITAL_EDGES):
        hopping[source, destination] = hopping[destination, source] = parameters[index]
    for index, (source, destination) in enumerate(VIRTUAL_EDGES):
        hopping[source, destination] = hopping[destination, source] = parameters[21 + index]
    for index, (source, destination) in enumerate(EDGE_PAIRS):
        density[source, destination] = density[destination, source] = parameters[42 + index]
    return hopping, density


def energy(mask, hopping, density, vectors=False):
    occupation, left, right, source, destination = TOPOLOGIES[mask]
    diagonal = occupation @ PAIR_ENERGY + 0.5 * np.sum((occupation @ density) * occupation, axis=1)
    matrix = np.diag(diagonal)
    matrix[left, right] = matrix[right, left] = hopping[source, destination]
    if vectors:
        eigenvalues, eigenvectors = eigh(matrix, subset_by_index=(0, 1), check_finite=False)
        return eigenvalues[0], eigenvalues[1] - eigenvalues[0], eigenvectors[0, 0] ** 2, np.min(diagonal[1:] - diagonal[0])
    return eigh(matrix, eigvals_only=True, subset_by_index=(0, 0), check_finite=False)[0]


def low_increments(parameters):
    hopping, density = decode(parameters)
    reference = energy(0, hopping, density)
    increments = np.zeros(128)
    for mask in LOW_MASKS[1:]:
        increments[mask] = energy(mask, hopping, density) - reference
        subset = (mask - 1) & mask
        while subset:
            increments[mask] -= increments[subset]
            subset = (subset - 1) & mask
    return increments, reference


def metrics(parameters):
    increments, reference = low_increments(parameters)
    full, gap, weight, margin = energy(127, *decode(parameters), vectors=True)
    tail = abs(full - reference - np.sum(increments))
    parent = np.max(np.abs(increments[TRIPLE_MASKS]))
    return dict(tail=tail, parent=parent, ratio=tail / max(parent, 1e-12), gap=gap, weight=weight, diagonal_margin=margin)


def residual(parameters, anchor, strength):
    increments, reference = low_increments(parameters)
    full, gap, weight, margin = energy(127, *decode(parameters), vectors=True)
    tail = full - reference - np.sum(increments)
    penalties = [min(0.0, gap - 0.43), min(0.0, weight - 0.953), min(0.0, margin - 0.60)]
    return np.concatenate((increments[TRIPLE_MASKS] * 1e5, np.array(penalties) * 100, [(tail - anchor) * strength]))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--restarts", type=int, default=4)
    parser.add_argument("--max-nfev", type=int, default=120)
    parser.add_argument("--seed", type=int, default=2718)
    parser.add_argument("--locked", action="store_true")
    arguments = parser.parse_args()
    generator = np.random.default_rng(arguments.seed)
    lower = np.array([-0.14] * 21 + [-0.45] * 21 + [-0.60] * 45)
    upper = -lower
    start = time.perf_counter()
    best_score = -1.0
    fixed_hopping = np.array([[0.045, -0.038, 0.052, 0.029, -0.047, 0.041, 0.034], [-0.031, 0.049, 0.036, -0.043, 0.028, 0.054, -0.039], [0.040, 0.032, -0.046, 0.051, 0.037, -0.030, 0.048]])
    variable_indices = np.array(list(range(21, 42)) + [42 + index for index, edge in enumerate(EDGE_PAIRS) if edge[0] >= 3])
    for restart in range(arguments.restarts):
        parameters = np.concatenate((generator.normal(0, 0.045, 21), generator.normal(0, 0.10, 21), generator.normal(0, 0.12, 45)))
        parameters = np.clip(parameters, lower + 1e-6, upper - 1e-6)
        if arguments.locked:
            parameters[:21] = fixed_hopping.ravel()
            parameters[42:] = 0.0
            def locked_residual(variables):
                candidate = parameters.copy()
                candidate[variable_indices] = variables
                return residual(candidate, -0.00010, 1e4)
            result = least_squares(locked_residual, parameters[variable_indices], bounds=(lower[variable_indices], upper[variable_indices]), max_nfev=arguments.max_nfev, ftol=1e-9, xtol=1e-9, gtol=1e-9)
            parameters[variable_indices] = result.x
        else:
            result = least_squares(residual, parameters, bounds=(lower, upper), args=(-0.00015, 1e4), max_nfev=arguments.max_nfev, ftol=1e-9, xtol=1e-9, gtol=1e-9)
            parameters = result.x
        diagnostic = metrics(parameters)
        diagnostic.update(restart=restart, nfev=result.nfev, elapsed=time.perf_counter() - start)
        print(json.dumps(diagnostic), flush=True)
        score = min(diagnostic["tail"] / 5e-5, diagnostic["ratio"] / 100, 1e-6 / max(diagnostic["parent"], 1e-12))
        if score > best_score:
            best_score = score
            hopping, density = decode(parameters)
            artifact = dict(schema_version=1, pair_energy=PAIR_ENERGY.tolist(), hopping=hopping.tolist(), density=density.tolist())
            prefix = "locked" if arguments.locked else "calibration"
            Path(__file__).with_name(prefix + "_witness.json").write_text(json.dumps(artifact, indent=2) + "\n")
            Path(__file__).with_name(prefix + "_metrics.json").write_text(json.dumps(diagnostic, indent=2) + "\n")


if __name__ == "__main__":
    main()
