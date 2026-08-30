import argparse
import json
from pathlib import Path
import time

from solve import load_atlas
import numpy as np
from scipy.optimize import linprog
from scipy.sparse import coo_matrix


def relaxation(atlas, limit=60, verbose=True):
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
    for face, corners in enumerate(atlas.plaquettes):
        descriptions = [(2 * corners[0], 0, 1), (2 * corners[1] + 1, 1, 2),
                        (2 * corners[3], 3, 2), (2 * corners[0] + 1, 0, 3)]
        for edge, first, second in descriptions:
            for first_label in range(4):
                for second_label in range(4):
                    selected = np.flatnonzero((assignments[:, first] == first_label) & (assignments[:, second] == second_label))
                    equation([edge_offset + 16 * edge + 4 * first_label + second_label] +
                             (face_offset + 256 * face + selected).tolist(), [-1] + [1] * 16)
    for scenario in range(4):
        equation(list(range(face_offset, variable_count - 1)),
                 (atlas.flux[scenario].reshape(-1) / (2 * np.pi)).tolist(), atlas.targets[scenario])
    equality = coo_matrix((entries, (rows, columns)), shape=(len(right_hand), variable_count)).tocsr()
    normalized = np.concatenate([atlas.unary.reshape(4, -1), atlas.pair.reshape(4, -1), atlas.face.reshape(4, -1)], axis=1) / atlas.normalizers[:, None]
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
    started = time.monotonic()
    result = linprog(objective, inequality, [0, 0, 0, 0, atlas.budget], equality, right_hand,
                     bounds=np.stack([np.zeros(variable_count), upper], axis=1), method='highs',
                     options={'time_limit': limit})
    if verbose:
        print('LP', result.message, result.fun, 'time', time.monotonic() - started, flush=True)
    if result.x is not None:
        marginal = result.x[:edge_offset].reshape(vertices, 4)
        choices = marginal.argmax(axis=1)
        if verbose:
            print('fractional', np.sum(marginal.max(axis=1) < .999), 'rounded score', atlas.score(choices), flush=True)
            np.savez('lp_result.npz', marginal=marginal, choices=choices, objective=result.fun)
        reduced = result.lower.marginals[:-1] + result.upper.marginals[:-1]
        starts = np.concatenate([np.arange(vertices) * 4,
                                 edge_offset + np.arange(2 * vertices) * 16,
                                 face_offset + np.arange(vertices) * 256])
        ends = np.concatenate([starts[1:], [variable_count - 1]])
        for start, end in zip(starts, ends):
            reduced[start:end] -= result.upper.marginals[start:end] @ upper[start:end]
        np.savez('lp_reduced.npz', reduced=reduced, objective=result.fun, marginal=marginal)
        result.reduced = reduced
        result.marginal = marginal
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--case', default='scenario_competition_0')
    parser.add_argument('--seconds', type=float, default=60)
    args = parser.parse_args()
    directory = Path(__file__).resolve().parents[2] / 'participant' / 'input' / args.case
    relaxation(load_atlas(directory), args.seconds)
