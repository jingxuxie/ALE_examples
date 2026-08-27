import numpy as np
from scipy.spatial import cKDTree


def characterize(cores, model):
    positions = cores[cores[:, 2] > 0, :2]
    positions = positions[model.sample(model.bulk, positions)]
    count = len(positions)
    boundaries = np.asarray(model.case['correlation_edges'])
    sums = np.zeros(len(boundaries) - 1)
    pairs = np.zeros(len(sums), dtype=int)
    local = np.zeros(count, dtype=complex)
    if count > 1:
        tree = cKDTree(positions)
        _, nearby = tree.query(positions, k=min(7, count))
        for index in range(count):
            delta = positions[nearby[index, 1:]] - positions[index]
            local[index] = np.mean(np.exp(6j * np.arctan2(delta[:, 1], delta[:, 0])))
        for first in range(count):
            for second in range(first + 1, count):
                distance = np.linalg.norm(positions[second] - positions[first])
                bucket = np.searchsorted(boundaries, distance, side='right') - 1
                if 0 <= bucket < len(sums):
                    sums[bucket] += np.abs(local[first]) ** 2
                    pairs[bucket] += 1
    counts = np.zeros(13, dtype=int)
    counts[min(6, max(0, count - 1))] = count
    return {'counts': counts.tolist(), 'correlations': np.divide(sums, pairs, out=np.zeros_like(sums), where=pairs > 0).tolist(), 'pair_counts': pairs.tolist(), 'defect_radius': 0.0}
