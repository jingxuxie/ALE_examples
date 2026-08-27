import numpy as np
from scipy.spatial import Delaunay, QhullError


def neighborhood(positions, model):
    labels = model.sample(model.roi, positions)
    neighbors = [set() for position in positions]
    for label in np.unique(labels):
        members = np.flatnonzero(labels == label)
        if label <= 0 or len(members) < 3:
            continue
        try:
            triangles = Delaunay(positions[members]).simplices
        except QhullError:
            continue
        edges = set()
        for triangle in triangles:
            for first, second in [(0, 1), (1, 2), (2, 0)]:
                edges.add(tuple(sorted((int(members[triangle[first]]), int(members[triangle[second]])))))
        for first, second in edges:
            distance = np.linalg.norm(positions[first] - positions[second])
            samples = max(3, int(np.ceil(distance / (min(model.dx, model.dy) / 2))) + 1)
            segment = np.linspace(positions[first], positions[second], samples)
            if np.all(model.sample(model.roi, segment) == label):
                neighbors[first].add(second)
                neighbors[second].add(first)
    return neighbors


def characterize(cores, model):
    positions = cores[cores[:, 2] > 0, :2]
    if getattr(model, 'crop_before_graph', False):
        positions = positions[model.sample(model.bulk, positions)]
    neighbors = neighborhood(positions, model)
    bulk = model.sample(model.bulk, positions)
    degree = np.asarray([len(adjacent) for adjacent in neighbors])
    order = np.zeros(len(positions), dtype=complex)
    for index, adjacent in enumerate(neighbors):
        if adjacent:
            difference = positions[list(adjacent)] - positions[index]
            order[index] = np.mean(np.exp(6j * np.arctan2(difference[:, 1], difference[:, 0])))
    indices = np.flatnonzero(bulk)
    boundaries = np.asarray(model.case['correlation_edges'])
    sums = np.zeros(len(boundaries) - 1)
    counts = np.zeros(len(boundaries) - 1, dtype=int)
    for index, first in enumerate(indices):
        second = indices[index + 1:]
        if len(second):
            distances = np.linalg.norm(positions[second] - positions[first], axis=1)
            correlations = (order[first] * np.conj(order[second])).real
            bins = np.searchsorted(boundaries, distances, side='right') - 1
            valid = (bins >= 0) & (bins < len(sums))
            np.add.at(sums, bins[valid], correlations[valid])
            np.add.at(counts, bins[valid], 1)
    correlations = np.divide(sums, counts, out=np.zeros_like(sums), where=counts > 0)
    defect_positions = positions[bulk & (degree != 6)]
    if len(defect_positions):
        center = np.asarray(model.case.get('intervention_center', [0, 0]))
        defect_radius = float(np.sqrt(np.mean(np.sum((defect_positions - center) ** 2, axis=1))))
    else:
        defect_radius = 0.0
    return {
        'counts': [int(np.sum(bulk & (degree == coordination))) for coordination in range(13)],
        'correlations': correlations.tolist(),
        'pair_counts': counts.tolist(),
        'defect_radius': defect_radius,
    }
