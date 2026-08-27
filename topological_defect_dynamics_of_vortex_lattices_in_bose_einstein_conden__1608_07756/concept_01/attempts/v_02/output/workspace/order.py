import numpy as np
from scipy.spatial import Delaunay, QhullError


def characterize(cores, model):
    positions = cores[cores[:, 2] > 0, :2]
    labels = model.sample(model.roi, positions)
    selected = model.sample(model.bulk, positions)
    neighbors = [set() for position in positions]
    edges = []
    for label in np.unique(labels):
        if label <= 0:
            continue
        members = np.flatnonzero(labels == label)
        candidates = set()
        if len(members) == 2:
            candidates.add(tuple(members))
        elif len(members) >= 3:
            try:
                triangles = Delaunay(positions[members]).simplices
                for triangle in triangles:
                    for offset in range(3):
                        candidates.add(tuple(sorted((members[triangle[offset]], members[triangle[(offset + 1) % 3]]))))
            except QhullError:
                centered = positions[members] - positions[members].mean(axis=0)
                direction = np.linalg.svd(centered, full_matrices=False)[2][0]
                ordered = members[np.argsort(centered @ direction)]
                candidates.update(zip(ordered[:-1], ordered[1:]))
        for first, second in sorted(candidates):
            displacement = positions[second] - positions[first]
            segments = max(1, int(np.ceil(np.linalg.norm(displacement) / (0.5 * min(model.dx, model.dy)))))
            samples = positions[first] + np.linspace(0, 1, segments + 1)[:, None] * displacement
            if np.all(model.sample(model.roi, samples) == label):
                neighbors[first].add(second)
                neighbors[second].add(first)
                edges.append([int(first), int(second)])
    coordination = np.asarray([len(adjacent) for adjacent in neighbors], dtype=int)
    local = np.zeros(len(positions), dtype=complex)
    for index, adjacent in enumerate(neighbors):
        if adjacent:
            delta = positions[sorted(adjacent)] - positions[index]
            local[index] = np.mean(np.exp(6j * np.arctan2(delta[:, 1], delta[:, 0])))
    boundaries = np.asarray(model.case['correlation_edges'])
    sums = np.zeros(len(boundaries) - 1)
    pairs = np.zeros(len(sums), dtype=int)
    bulk_indices = np.flatnonzero(selected)
    for offset, first in enumerate(bulk_indices):
        seconds = bulk_indices[offset + 1:]
        distance = np.linalg.norm(positions[seconds] - positions[first], axis=1)
        buckets = np.searchsorted(boundaries, distance, side='right') - 1
        valid = (buckets >= 0) & (buckets < len(sums))
        correlations = np.real(local[first] * np.conj(local[seconds]))
        np.add.at(sums, buckets[valid], correlations[valid])
        np.add.at(pairs, buckets[valid], 1)
    counts = np.bincount(coordination[selected], minlength=13)[:13]
    defects = positions[selected & (coordination != 6)]
    center = np.asarray(model.case.get('intervention_center', [0, 0]))
    radius = float(np.sqrt(np.mean(np.sum((defects - center) ** 2, axis=1)))) if len(defects) else 0.0
    return {'counts': counts.tolist(),
            'correlations': np.divide(sums, pairs, out=np.zeros_like(sums), where=pairs > 0).tolist(),
            'pair_counts': pairs.tolist(), 'defect_radius': radius,
            'positions': positions.tolist(), 'coordination': coordination.tolist(),
            'local_order': np.column_stack((local.real, local.imag)).tolist(),
            'bulk': selected.tolist(), 'labels': labels.tolist(), 'edges': edges}
