"""A small unconstrained dual-ridge starting point."""

import os
import sys

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"

import numpy as np


def ridge_coefficients(features, targets):
    gram = features @ features.T
    penalty = max(float(np.trace(gram)) / max(len(gram), 1), 1.0) * 1e-5
    gram.flat[:: len(gram) + 1] += penalty
    return features.T @ np.linalg.solve(gram, targets)


def harmonic_fit(displacements, forces, representatives):
    flattened = displacements.reshape(len(displacements), -1)
    scale = max(float(np.sqrt(np.mean(flattened**2))), 1e-8)
    targets = -forces[:, representatives].reshape(len(forces), -1)
    coefficients = ridge_coefficients(flattened / scale, targets) / scale
    atom_count = displacements.shape[1]
    return coefficients.T.reshape(len(representatives), 3, atom_count, 3).transpose(0, 2, 1, 3)


def fold_harmonic(fc2, fold, atom_count):
    folded = np.zeros((len(fc2), atom_count, 3, 3))
    for representative in range(len(fc2)):
        np.add.at(folded[representative], fold[representative], fc2[representative])
    return folded


def harmonic_forces(fc2, displacements, row_map, compact_map):
    expanded = fc2[row_map[:, None], compact_map]
    return -np.einsum("ijab,sjb->sia", expanded, displacements, optimize=True)


def mixed_fit(displacements, forces, representatives, joint):
    atom_count = displacements.shape[1]
    flattened = displacements.reshape(len(displacements), -1)
    coordinate_count = flattened.shape[1]
    scale = max(float(np.sqrt(np.mean(flattened**2))), 1e-8)
    normalized = flattened / scale
    first, second = np.triu_indices(coordinate_count)
    factors = np.where(first == second, 0.5, 1.0)
    quadratic_weight = 0.1 / np.sqrt(coordinate_count)
    quadratic = normalized[:, first] * normalized[:, second] * factors * quadratic_weight
    features = np.concatenate((normalized, quadratic), axis=1) if joint else quadratic
    targets = -forces[:, representatives].reshape(len(forces), -1)
    coefficients = ridge_coefficients(features, targets)
    if joint:
        harmonic = coefficients[:coordinate_count].T / scale
        fc2 = harmonic.reshape(len(representatives), 3, atom_count, 3).transpose(0, 2, 1, 3)
        coefficients = coefficients[coordinate_count:]
    else:
        fc2 = None
    coefficients = coefficients.T * quadratic_weight / scale**2
    cubic = np.zeros((len(representatives) * 3, coordinate_count, coordinate_count))
    cubic[:, first, second] = coefficients
    cubic[:, second, first] = coefficients
    fc3 = cubic.reshape(len(representatives), 3, atom_count, 3, atom_count, 3).transpose(0, 2, 4, 1, 3, 5)
    return fc2, fc3


def solve(data):
    if int(data["fit_mode"]) == 0:
        fc2, fc3 = mixed_fit(data["u3"], data["f3"], data["p2s3"], True)
    else:
        fc2 = harmonic_fit(data["u2"], data["f2"], data["p2s2"])
        small = fold_harmonic(fc2, data["fold2to3"], len(data["numbers3"]))
        residual = data["f3"] - harmonic_forces(small, data["u3"], data["s2p3"], data["compact_map3"])
        _, fc3 = mixed_fit(data["u3"], residual, data["p2s3"], False)
    fc3 *= data["triplet_mask3"][..., None, None, None]
    return {"fc2": np.asarray(fc2, dtype=np.float64), "fc3": np.asarray(fc3, dtype=np.float64)}


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: python solve.py INPUT.npz OUTPUT.npz")
    with np.load(sys.argv[1], allow_pickle=False) as loaded:
        result = solve(loaded)
    with open(sys.argv[2], "wb") as output:
        np.savez_compressed(output, **result)


if __name__ == "__main__":
    main()
