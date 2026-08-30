import numpy as np
from scipy.linalg import eigvalsh, solve
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components


def laplacian(state_count, source, target, weights):
    matrix = np.zeros((state_count, state_count))
    matrix[source, target] = -weights
    matrix[target, source] = -weights
    matrix[np.diag_indices(state_count)] = -matrix.sum(axis=1)
    return matrix


def observables(matrix, velocities, probes):
    state_count = matrix.shape[0]
    shifted = matrix + np.ones_like(matrix) / state_count
    response = solve(shifted, velocities, assume_a='pos')
    conductivity = velocities.T @ response / state_count
    dissipation = np.sum(probes * (matrix @ probes), axis=0) / state_count
    return np.diag(matrix), conductivity, dissipation


def validate(catalogue, indices, multipliers):
    edge_count = len(catalogue['source'])
    state_count = len(catalogue['velocities'])
    if indices.ndim != 1 or indices.dtype.kind not in 'iu':
        raise ValueError('indices must be a one-dimensional integer array')
    if multipliers.ndim != 1 or multipliers.shape != indices.shape or multipliers.dtype.kind not in 'fiu':
        raise ValueError('multipliers must align with indices')
    if not 0 < len(indices) <= int(catalogue['budget']):
        raise ValueError('event budget exceeded or empty output')
    if len(np.unique(indices)) != len(indices) or np.any(indices < 0) or np.any(indices >= edge_count):
        raise ValueError('invalid or duplicate event indices')
    if not np.all(np.isfinite(multipliers)) or np.any(multipliers < 0) or np.any(multipliers > 1e9):
        raise ValueError('multipliers must be finite, nonnegative, and at most 1e9')
    positive = multipliers > 0
    graph = coo_matrix((np.ones(positive.sum()),
                        (catalogue['source'][indices[positive]], catalogue['target'][indices[positive]])),
                       shape=(state_count, state_count))
    if connected_components(graph, directed=False, return_labels=False) != 1:
        raise ValueError('retained collision graph is disconnected')


def score(catalogue, indices, multipliers):
    validate(catalogue, indices, multipliers)
    source = catalogue['source']
    target = catalogue['target']
    channels = catalogue['channels']
    velocities = catalogue['velocities']
    probes = catalogue['probes']
    state_count = len(velocities)
    rows = []
    for coefficients in catalogue['mixing']:
        weights = channels @ coefficients
        original = laplacian(state_count, source, target, weights)
        compressed = laplacian(state_count, source[indices], target[indices], weights[indices] * multipliers)
        degree, conductivity, dissipation = observables(original, velocities, probes)
        degree_new, conductivity_new, dissipation_new = observables(compressed, velocities, probes)
        degree_error = float(np.sqrt(np.mean(((degree_new / degree) - 1.0) ** 2)))
        conductivity_error = float(np.max(np.abs(eigvalsh(conductivity_new - conductivity, conductivity))))
        dissipation_error = float(np.max(np.abs(dissipation_new / dissipation - 1.0)))
        rows.append({'degree_rms': degree_error, 'conductivity_operator': conductivity_error,
                     'probe_dissipation': dissipation_error})
    error = max(value for row in rows for value in row.values())
    if not np.isfinite(error):
        raise ValueError('nonfinite physical diagnostic')
    return {'score': float(100 * np.exp(-error / 0.05)), 'relative_error': error,
            'diagnostics': rows, 'retained_edges': len(indices), 'budget': int(catalogue['budget'])}
