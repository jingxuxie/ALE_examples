import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
import itertools
import json
import sys
import time
from pathlib import Path
import numpy as np
from scipy.optimize import linprog
from scipy.sparse import coo_matrix

ROOT = Path(__file__).resolve().parents[2] / 'participant'
sys.path.insert(0, str(ROOT / 'workspace'))
from atlas import Atlas


def relaxation(atlas, seconds=20):
    candidates = 4
    vertex_count = atlas.vertices
    edge_count = len(atlas.edges)
    face_count = len(atlas.plaquettes)
    order = np.argsort(atlas.costs, axis=1)
    unary_count = vertex_count * candidates
    pair_count = edge_count * candidates ** 2
    quad_count = face_count * candidates ** 4
    variable_count = unary_count + pair_count + quad_count + 1
    losses = np.zeros((4, variable_count))
    fluxes = np.zeros((4, variable_count))
    acquisition = np.zeros(variable_count)
    bounds = np.zeros((variable_count, 2))
    bounds[:, 1] = 1
    bounds[-1, 1] = np.inf
    for vertex in range(vertex_count):
        for choice in range(candidates):
            index = vertex * candidates + choice
            label = order[vertex, choice]
            losses[:, index] = atlas.unary[:, vertex, label]
            acquisition[index] = atlas.costs[vertex, label]
            if vertex in atlas.anchors and label != atlas.anchors[vertex]:
                bounds[index, 1] = 0
    for edge, (source, destination) in enumerate(atlas.edges):
        for first, second in itertools.product(range(candidates), repeat=2):
            index = unary_count + edge * candidates ** 2 + first * candidates + second
            first_label, second_label = order[source, first], order[destination, second]
            losses[:, index] = atlas.pair[:, edge, first_label, second_label]
            if np.any(atlas.link_magnitude[:, edge, first_label, second_label] < atlas.minimum_link):
                bounds[index, 1] = 0
    for face, corners in enumerate(atlas.plaquettes):
        for choices in itertools.product(range(candidates), repeat=4):
            offset = ((choices[0] * candidates + choices[1]) * candidates + choices[2]) * candidates + choices[3]
            index = unary_count + pair_count + face * candidates ** 4 + offset
            labels = order[corners, choices]
            losses[:, index] = atlas.face[(slice(None), face, *labels)]
            fluxes[:, index] = atlas.flux[(slice(None), face, *labels)]
            if np.any(np.pi - np.abs(fluxes[:, index]) < atlas.branch_margin):
                bounds[index, 1] = 0
    losses /= atlas.normalizers[:, None]
    objective = (atlas.mean_weight * atlas.weights / atlas.weights.sum()) @ losses
    objective[-1] = 1
    rows, columns, values, right_hand = [], [], [], []
    def add_row(indices, coefficients, target):
        rows.extend([len(right_hand)] * len(indices))
        columns.extend(indices)
        values.extend(coefficients)
        right_hand.append(target)
    for vertex in range(vertex_count):
        add_row(list(range(vertex * candidates, (vertex + 1) * candidates)), [1] * candidates, 1)
    for edge, (source, destination) in enumerate(atlas.edges):
        for position, vertex in enumerate((source, destination)):
            for choice in range(candidates):
                indices = [vertex * candidates + choice]
                coefficients = [-1]
                for other in range(candidates):
                    offset = choice * candidates + other if position == 0 else other * candidates + choice
                    indices.append(unary_count + edge * candidates ** 2 + offset)
                    coefficients.append(1)
                add_row(indices, coefficients, 0)
    tuples = list(itertools.product(range(candidates), repeat=4))
    for face, corners in enumerate(atlas.plaquettes):
        edges = [(2 * corners[0], 0, 1), (2 * corners[1] + 1, 1, 2),
                 (2 * corners[3], 3, 2), (2 * corners[0] + 1, 0, 3)]
        for edge, first_position, second_position in edges:
            for first, second in itertools.product(range(candidates), repeat=2):
                indices = [unary_count + edge * candidates ** 2 + first * candidates + second]
                coefficients = [-1]
                for offset, choices in enumerate(tuples):
                    if choices[first_position] == first and choices[second_position] == second:
                        indices.append(unary_count + pair_count + face * candidates ** 4 + offset)
                        coefficients.append(1)
                add_row(indices, coefficients, 0)
    for scenario in range(4):
        indices = np.flatnonzero(fluxes[scenario])
        add_row(indices.tolist(), fluxes[scenario, indices].tolist(), 2 * np.pi * atlas.targets[scenario])
    equalities = coo_matrix((values, (rows, columns)), shape=(len(right_hand), variable_count)).tocsr()
    inequalities = np.vstack((acquisition, losses))
    inequalities[1:, -1] = -1
    inequality_targets = np.array([atlas.budget, 0, 0, 0, 0])
    started = time.monotonic()
    result = linprog(objective, A_eq=equalities, b_eq=right_hand,
                     A_ub=inequalities, b_ub=inequality_targets,
                     bounds=bounds, method='highs', options={'time_limit': seconds})
    print('LP', time.monotonic() - started, result.message, flush=True)
    if result.x is not None:
        probabilities = result.x[:unary_count].reshape(vertex_count, candidates)
        choice = order[np.arange(vertex_count), np.argmax(probabilities, axis=1)]
        print('bound', result.fun, 'fractional', np.sum(np.max(probabilities, axis=1) < 0.99999), flush=True)
        print('rounding', atlas.score(choice), flush=True)
        return order, probabilities


if __name__ == '__main__':
    for case in json.loads((ROOT / 'input' / 'manifest.json').read_text())['cases']:
        atlas = Atlas.load(ROOT / 'input' / case['directory'])
        print(case['id'], flush=True)
        result = relaxation(atlas)
        if result is not None:
            np.savez(Path(__file__).with_name(case['id'] + '_relax.npz'), order=result[0], probabilities=result[1])
