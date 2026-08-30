import numpy as np
from scipy.optimize import linprog
from scipy.sparse import coo_matrix


def relaxation(atlas, seconds):
    vertices = atlas.vertices
    edge_offset = 4 * vertices
    face_offset = edge_offset + 32 * vertices
    variable_count = face_offset + 256 * vertices + 1
    rows, columns, entries, right_hand = [], [], [], []

    def equation(indices, values, rhs=0):
        row = len(right_hand)
        rows.extend([row] * len(indices))
        columns.extend(indices)
        entries.extend(values)
        right_hand.append(rhs)

    for vertex in range(vertices):
        equation(list(range(4 * vertex, 4 * vertex + 4)), [1] * 4, 1)
    edge_indices = np.arange(16).reshape(4, 4)
    for edge, endpoints in enumerate(atlas.edges):
        for position, vertex in enumerate(endpoints):
            for label in range(4):
                selected = edge_indices[label, :] if position == 0 else edge_indices[:, label]
                equation([4 * vertex + label] + (edge_offset + 16 * edge + selected).tolist(), [-1] + [1] * 4)
    assignments = np.indices((4, 4, 4, 4)).reshape(4, -1).T
    selected_assignments = {}
    for first, second in [(0, 1), (1, 2), (3, 2), (0, 3)]:
        for first_label in range(4):
            for second_label in range(4):
                selected_assignments[first, second, first_label, second_label] = np.flatnonzero(
                    (assignments[:, first] == first_label) & (assignments[:, second] == second_label))
    for face, corners in enumerate(atlas.plaquettes):
        descriptions = [(2 * corners[0], 0, 1), (2 * corners[1] + 1, 1, 2),
                        (2 * corners[3], 3, 2), (2 * corners[0] + 1, 0, 3)]
        for edge, first, second in descriptions:
            for first_label in range(4):
                for second_label in range(4):
                    selected = selected_assignments[first, second, first_label, second_label]
                    equation([edge_offset + 16 * edge + 4 * first_label + second_label] +
                             (face_offset + 256 * face + selected).tolist(), [-1] + [1] * 16)
    for scenario in range(4):
        equation(list(range(face_offset, variable_count - 1)),
                 (atlas.flux[scenario].reshape(-1) / (2 * np.pi)).tolist(), atlas.targets[scenario])
    equality = coo_matrix((entries, (rows, columns)), shape=(len(right_hand), variable_count)).tocsr()
    normalized = np.concatenate([atlas.unary.reshape(4, -1), atlas.pair.reshape(4, -1),
                                 atlas.face.reshape(4, -1)], axis=1) / atlas.normalizers[:, None]
    objective = np.zeros(variable_count)
    objective[:-1] = atlas.mean_weight * atlas.weights @ normalized / atlas.weights.sum()
    objective[-1] = 1
    inequality = np.zeros((5, variable_count))
    inequality[:4, :-1] = normalized
    inequality[:4, -1] = -1
    inequality[4, :edge_offset] = atlas.costs.reshape(-1)
    upper = np.ones(variable_count)
    upper[-1] = np.inf
    upper[edge_offset:face_offset] = (atlas.link_magnitude.min(axis=0).reshape(-1) >= atlas.minimum_link)
    upper[face_offset:-1] = (np.abs(atlas.flux).max(axis=0).reshape(-1) <= np.pi - atlas.branch_margin)
    for vertex, label in atlas.anchors.items():
        upper[4 * vertex:4 * vertex + 4] = 0
        upper[4 * vertex + label] = 1
    result = linprog(objective, inequality, [0, 0, 0, 0, atlas.budget], equality, right_hand,
                     bounds=np.stack([np.zeros(variable_count), upper], axis=1), method='highs',
                     options={'time_limit': seconds})
    if not result.success:
        return None
    reduced = result.lower.marginals[:-1] + result.upper.marginals[:-1]
    starts = np.concatenate([np.arange(vertices) * 4,
                             edge_offset + np.arange(2 * vertices) * 16,
                             face_offset + np.arange(vertices) * 256])
    ends = np.concatenate([starts[1:], [variable_count - 1]])
    for start, end in zip(starts, ends):
        reduced[start:end] -= result.upper.marginals[start:end] @ upper[start:end]
    return float(result.fun), np.ascontiguousarray(reduced), result.x[:edge_offset].reshape(vertices, 4)
