"""Permutation-invariant low-order and diagonal descriptors, without labels."""

from itertools import combinations

import numpy as np


PAIRS = np.asarray(list(combinations(range(9), 2)), dtype=int)
TRIPLES = np.asarray(list(combinations(range(9), 3)), dtype=int)


def statistics(values):
    values = np.asarray(values, dtype=float).ravel()
    return [values.mean(), values.std(), values.min(), values.max(), values.sum(),
            np.abs(values).sum(), np.linalg.norm(values), *np.quantile(values, [.1, .25, .5, .75, .9])]


def featurize(data):
    rows, scales = [], []
    for row in range(len(data["ids"])):
        n_virtual = int(data["n_virtual"][row])
        n_pairs = int(data["n_pairs"][row])
        pair_mask = PAIRS[:, 1] < n_virtual
        triple_mask = TRIPLES[:, 2] < n_virtual
        first = data["inc1"][row, :n_virtual]
        second = data["inc2"][row, pair_mask]
        third = data["inc3"][row, triple_mask]
        gaps = data["diagonal_gaps"][row, :n_pairs, :n_virtual]
        energy_scale = float(gaps.mean())
        signs = data["pair_sign"][row, pair_mask]
        sums = np.asarray([first.sum(), second.sum(), third.sum()])
        absolute = np.asarray([np.abs(values).sum() for values in (first, second, third)])
        target_scale = max(absolute[2], 1e-5)
        scales.append(target_scale)
        ratio_second = sums[1] / max(absolute[0], 1e-12)
        ratio_third = sums[2] / max(absolute[1], 1e-12)
        descriptors = [n_pairs, n_virtual, energy_scale, *sums / energy_scale,
                       *absolute / energy_scale, ratio_second, ratio_third,
                       sums[2] / target_scale, (n_virtual - 3) / max(n_virtual - 2, 1),
                       *np.eye(6)[int(data["family"][row])]]
        for values in (first / energy_scale, second / energy_scale, third / energy_scale,
                       gaps / energy_scale, signs,
                       data["occupied_profile"][row, :n_pairs],
                       data["density"][row, :n_pairs + n_virtual, :n_pairs + n_virtual] / energy_scale):
            descriptors.extend(statistics(values))
        pair_graph = np.zeros((n_virtual, n_virtual))
        sign_graph = np.zeros_like(pair_graph)
        for index, (left, right) in enumerate(PAIRS[pair_mask]):
            normalization = np.sqrt(abs(first[left] * first[right])) + 1e-12
            pair_graph[left, right] = second[index] / normalization
            pair_graph[right, left] = pair_graph[left, right]
            sign_graph[left, right] = signs[index]
            sign_graph[right, left] = signs[index]
        triple_strength = np.zeros(n_virtual)
        for increment, triple in zip(third, TRIPLES[triple_mask]):
            triple_strength[triple] += increment
        for graph in (pair_graph, sign_graph / n_virtual):
            eigenvalues = np.linalg.eigvalsh(graph)
            descriptors.extend(statistics(eigenvalues))
            descriptors.extend(statistics(graph.sum(axis=1)))
            descriptors.extend([np.sum(eigenvalues ** power) for power in (3, 4, 5, 6)])
            descriptors.extend([first @ np.linalg.matrix_power(graph, power) @ first /
                                (energy_scale ** 2) for power in (1, 2, 3)])
        descriptors.extend(statistics(triple_strength / target_scale))
        descriptors.extend(statistics(first / gaps.mean(axis=0)))
        rows.append(descriptors)
    return np.asarray(rows), np.asarray(scales)


def rmse(target, prediction):
    return float(np.sqrt(np.mean(np.square(target - prediction))))


def metrics(target, prediction, family):
    errors = target - prediction
    per_family = {str(int(value)): rmse(target[family == value], prediction[family == value])
                  for value in np.unique(family)}
    return {"core_score": rmse(target, prediction),
            "worst_family_score": max(per_family.values()),
            "family_rmse": per_family, "mae": float(np.abs(errors).mean()),
            "p95_absolute_error": float(np.quantile(np.abs(errors), .95)),
            "max_absolute_error": float(np.abs(errors).max())}
