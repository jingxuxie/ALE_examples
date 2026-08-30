import os

os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['NUMEXPR_NUM_THREADS'] = '1'

import argparse
import time

import numpy as np
from scipy.linalg import eigh, solve
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components, minimum_spanning_tree

from bounded import bounded_fit


def compress(catalogue):
    started = time.monotonic()
    deadline = started + 75.0
    original_indices = np.flatnonzero(np.any(catalogue['channels'] > 0, axis=1))
    budget = min(int(catalogue['budget']), len(original_indices))
    if budget == len(original_indices):
        return original_indices, np.ones(budget)
    source = catalogue['source'][original_indices]
    target = catalogue['target'][original_indices]
    channels = catalogue['channels'][original_indices]
    velocities = np.asarray(catalogue['velocities'], dtype=float)
    probes = np.asarray(catalogue['probes'], dtype=float)
    state_count, probe_count = probes.shape
    edge_count = len(source)
    full_indices = np.arange(edge_count)
    weights = catalogue['mixing'] @ channels.T
    temperature_count = len(weights)
    incidence = np.zeros((state_count, edge_count))
    incidence[source, full_indices] = 1
    incidence[target, full_indices] = 1
    degrees = weights @ incidence.T
    normalization = degrees.mean(axis=1)
    weights /= normalization[:, None]
    degrees /= normalization[:, None]
    probe_delta = (probes[source] - probes[target]).T ** 2
    dissipations = weights @ probe_delta.T
    shift = np.ones((state_count, state_count)) / state_count
    diagonal = np.diag_indices(state_count)
    tensor_rows, tensor_columns = np.triu_indices(3)
    tensor_scale = np.where(tensor_rows == tensor_columns, 1., np.sqrt(2.))
    degree_importance = np.mean(
        weights * (1 / degrees[:, source] + 1 / degrees[:, target]), axis=0)
    leverage = np.zeros(edge_count)
    transport = np.zeros(edge_count)
    original_responses = []
    whitened_drives = []
    for temperature in range(temperature_count):
        matrix = np.zeros_like(shift)
        matrix[source, target] = -weights[temperature]
        matrix[target, source] = -weights[temperature]
        matrix[diagonal] = degrees[temperature]
        inverse = solve(matrix + shift, np.eye(state_count), assume_a='pos', check_finite=False)
        resistance = inverse[source, source] + inverse[target, target] - 2 * inverse[source, target]
        leverage += weights[temperature] * np.maximum(resistance, 0) / temperature_count
        response = inverse @ velocities
        conductivity = velocities.T @ response
        eigenvalues, eigenvectors = eigh(conductivity, check_finite=False)
        transform = eigenvectors / np.sqrt(eigenvalues)
        response = response @ transform
        whitened_drives.append(velocities @ transform)
        original_responses.append(response)
        difference = response[source] - response[target]
        transport += weights[temperature] * np.sum(difference ** 2, axis=1) / temperature_count
    importance = .2 * degree_importance + .3 * leverage + .1 * state_count * transport
    importance = np.maximum(importance, np.finfo(float).tiny)
    scale = 1 / importance
    linear = np.concatenate([
        incidence * weights[temperature] / degrees[temperature, :, None] / np.sqrt(state_count)
        for temperature in range(temperature_count)
    ] + [
        probe_delta * weights[temperature] / dissipations[temperature, :, None] / np.sqrt(probe_count)
        for temperature in range(temperature_count)
    ])
    linear *= scale
    linear_target = linear @ importance

    def tensor_features(indices, values=None, feature_indices=None):
        if feature_indices is None:
            feature_indices = indices
        features, residuals = [], []
        for temperature in range(temperature_count):
            if values is None:
                response = original_responses[temperature]
                conductivity = np.eye(3)
            else:
                multipliers = np.maximum(scale[indices] * values, 1e-10)
                selected_weights = weights[temperature, indices] * multipliers
                matrix = np.zeros_like(shift)
                matrix[source[indices], target[indices]] = -selected_weights
                matrix[target[indices], source[indices]] = -selected_weights
                matrix[diagonal] = -matrix.sum(axis=1)
                response = solve(matrix + shift, whitened_drives[temperature],
                                 assume_a='pos', check_finite=False)
                conductivity = whitened_drives[temperature].T @ response
            difference = response[source[feature_indices]] - response[target[feature_indices]]
            feature = difference[:, tensor_rows] * difference[:, tensor_columns]
            features.append((feature * (weights[temperature, feature_indices] * scale[feature_indices])[:, None] * tensor_scale).T)
            residuals.append((conductivity - np.eye(3))[tensor_rows, tensor_columns] * tensor_scale)
        return np.concatenate(features), np.concatenate(residuals)

    def diagnostics(linear_residual, tensor_residual):
        degree_errors = np.linalg.norm(
            linear_residual[:temperature_count * state_count].reshape(temperature_count, state_count), axis=1)
        probe_errors = np.abs(linear_residual[temperature_count * state_count:]) * np.sqrt(probe_count)
        tensors = np.zeros((temperature_count, 3, 3))
        upper = tensor_residual.reshape(temperature_count, 6) / tensor_scale
        tensors[:, tensor_rows, tensor_columns] = upper
        tensors[:, tensor_columns, tensor_rows] = upper
        tensor_errors = np.max(np.abs(np.linalg.eigvalsh(tensors)), axis=1)
        error = max(degree_errors.max(), probe_errors.max(), tensor_errors.max())
        return error, degree_errors, probe_errors, tensor_errors

    lookup = np.full((state_count, state_count), -1, dtype=int)
    lookup[source, target] = full_indices
    lookup[target, source] = full_indices

    def spanning_tree(indices, priorities):
        graph = coo_matrix((-np.maximum(priorities, 1e-100),
                            (source[indices], target[indices])), shape=(state_count, state_count)).tocsr()
        tree = minimum_spanning_tree(graph).tocoo()
        return lookup[tree.row, tree.col]

    def prune(indices, values):
        keep = np.argsort(values)[-budget:]
        selected = indices[keep]
        graph = coo_matrix((np.ones(len(selected)), (source[selected], target[selected])),
                           shape=(state_count, state_count))
        if connected_components(graph, directed=False, return_labels=False) != 1:
            required = spanning_tree(indices, values)
            priority = values.copy()
            priority[np.isin(indices, required)] = np.inf
            keep = np.argsort(priority)[-budget:]
        return indices[keep], values[keep]

    def exchange_support(features, targets, indices, values, ridge):
        residual = targets - features[:, indices] @ values
        column_norms = np.maximum(np.linalg.norm(features, axis=0), 1e-100)
        correlations = features.T @ residual / column_norms
        correlations[indices] = -np.inf
        candidates = []
        endpoint_counts = np.zeros(state_count, dtype=int)
        for candidate in np.argsort(correlations)[::-1]:
            if correlations[candidate] <= 0 or len(candidates) >= budget // 5:
                break
            if max(endpoint_counts[source[candidate]], endpoint_counts[target[candidate]]) >= 4:
                continue
            candidates.append(candidate)
            endpoint_counts[source[candidate]] += 1
            endpoint_counts[target[candidate]] += 1
        if not candidates:
            return indices, values
        enlarged = np.concatenate([indices, candidates]).astype(int)
        reference = np.concatenate([values, np.zeros(len(candidates))])
        enlarged_values = bounded_fit(features[:, enlarged], targets, initial=reference,
                                      ridge=ridge, reference=reference if ridge > 1e-8 else None)
        selected, initial = prune(enlarged, enlarged_values)
        fitted = bounded_fit(features[:, selected], targets, initial=initial,
                             ridge=ridge, reference=initial if ridge > 1e-8 else None)
        return selected, fitted

    generator = np.random.default_rng(42)
    priorities = importance / generator.exponential(size=edge_count)
    priorities[spanning_tree(full_indices, importance)] = np.inf
    indices = np.argsort(priorities)[-budget:]
    initial_tensor, _ = tensor_features(full_indices)
    initial_features = np.concatenate([linear, initial_tensor])
    initial_target = initial_features @ importance
    values = bounded_fit(initial_features[:, indices], initial_target)
    for iteration in range(4):
        if time.monotonic() > deadline - 12:
            break
        initial_residual = initial_target - initial_features[:, indices] @ values
        if np.max(np.abs(initial_residual)) < 3e-5:
            break
        indices, values = exchange_support(initial_features, initial_target, indices, values, 1e-8)
    del initial_features, initial_tensor

    damping = 9e-6
    best_error = np.inf
    best_indices, best_values = indices.copy(), values.copy()
    row_weights = np.ones(len(linear_target) + 6 * temperature_count)
    selected_linear = linear[:, indices]
    for iteration in range(54):
        tensor, tensor_residual = tensor_features(indices, values)
        linear_residual = linear_target - selected_linear @ values
        error, degree_errors, probe_errors, tensor_errors = diagnostics(linear_residual, tensor_residual)
        if error < best_error:
            best_error = error
            best_indices, best_values = indices.copy(), values.copy()
        if best_error < 3e-5 or time.monotonic() > deadline - 8:
            break
        if iteration >= 24 and iteration % 8 == 0 and best_error > .0005:
            row_weights = np.concatenate([
                np.repeat(np.maximum(.2, degree_errors / error), state_count),
                np.maximum(.2, probe_errors / error) * np.sqrt(probe_count),
                np.repeat(np.maximum(.2, tensor_errors / error), 6)
            ])
            damping = max(damping, 1e-6)
        residual = np.concatenate([linear_residual, tensor_residual])
        objective = np.linalg.norm(row_weights * residual) ** 2
        if iteration >= 6 and iteration % 6 == 0 and error > 5e-5:
            full_tensor, _ = tensor_features(indices, values, full_indices)
            features = np.concatenate([linear, full_tensor])
            targets = np.concatenate([linear_target, tensor @ values + tensor_residual])
            next_indices, next_values = exchange_support(
                row_weights[:, None] * features, row_weights * targets,
                indices, values, max(damping, 1e-7))
            try:
                _, next_tensor_residual = tensor_features(next_indices, next_values)
                next_linear_residual = linear_target - linear[:, next_indices] @ next_values
                next_residual = np.concatenate([next_linear_residual, next_tensor_residual])
                next_objective = np.linalg.norm(row_weights * next_residual) ** 2
            except np.linalg.LinAlgError:
                next_objective = np.inf
            del features, full_tensor
            if next_objective < objective:
                indices, values = next_indices, next_values
                selected_linear = linear[:, indices]
                continue
        features = np.concatenate([selected_linear, tensor])
        targets = np.concatenate([linear_target, tensor @ values + tensor_residual])
        proposal = bounded_fit(row_weights[:, None] * features, row_weights * targets,
                               initial=values, ridge=damping, reference=values)
        step = 1.
        accepted = False
        while step > .005:
            updated = values + step * (proposal - values)
            try:
                _, next_tensor_residual = tensor_features(indices, updated)
                next_linear_residual = linear_target - selected_linear @ updated
                next_residual = np.concatenate([next_linear_residual, next_tensor_residual])
                next_objective = np.linalg.norm(row_weights * next_residual) ** 2
            except np.linalg.LinAlgError:
                next_objective = np.inf
            if next_objective < objective:
                values = updated
                accepted = True
                break
            step *= .5
        if not accepted:
            damping *= 10
            if damping > .01:
                break
        elif step == 1:
            damping = max(1e-9, damping * .6)
        elif step <= .25:
            damping = min(.01, damping * 4)
    _, tensor_residual = tensor_features(indices, values)
    linear_residual = linear_target - linear[:, indices] @ values
    error = diagnostics(linear_residual, tensor_residual)[0]
    if error < best_error:
        best_indices, best_values = indices, values
    multipliers = np.clip(scale[best_indices] * best_values, 1e-10, 1e9)
    order = np.argsort(original_indices[best_indices])
    return original_indices[best_indices][order], multipliers[order]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    arguments = parser.parse_args()
    with np.load(arguments.input, allow_pickle=False) as catalogue:
        indices, multipliers = compress(catalogue)
    np.savez(arguments.output, indices=indices.astype(np.int64), multipliers=multipliers)


if __name__ == '__main__':
    main()
