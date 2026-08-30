import heapq
import itertools
import os
import time

import numpy as np
from scipy.optimize import linprog
from scipy.sparse import coo_matrix, csr_matrix


class Relaxation:
    def __init__(self, atlas):
        self.atlas = atlas
        self.vertex_count = atlas.vertices
        self.unary_count = 4 * atlas.vertices
        self.pair_count = 16 * len(atlas.edges)
        self.face_offset = self.unary_count + self.pair_count
        self.variable_count = self.face_offset + 256 * len(atlas.plaquettes) + 1
        losses = np.concatenate([
            np.moveaxis(values / atlas.normalizers.reshape((-1,) + (1,) * (values.ndim - 1)), 0, -1).reshape(-1, 4)
            for values in (atlas.unary, atlas.pair, atlas.face)
        ]).T
        self.objective = np.zeros(self.variable_count)
        self.objective[:-1] = (atlas.mean_weight * atlas.weights / atlas.weights.sum()) @ losses
        self.objective[-1] = 1
        self.bounds = np.zeros((self.variable_count, 2))
        self.bounds[:, 1] = 1
        self.bounds[-1, 1] = np.inf
        invalid_pairs = np.any(atlas.link_magnitude < atlas.minimum_link, axis=0).reshape(-1)
        invalid_faces = np.any(np.pi - np.abs(atlas.flux) < atlas.branch_margin, axis=0).reshape(-1)
        self.bounds[self.unary_count:self.face_offset, 1] = ~invalid_pairs
        self.bounds[self.face_offset:-1, 1] = ~invalid_faces
        for vertex, choice in atlas.anchors.items():
            self.bounds[4 * vertex:4 * vertex + 4, 1] = 0
            self.bounds[4 * vertex + choice, 1] = 1
        inequalities = np.zeros((5, self.variable_count))
        inequalities[0, :self.unary_count] = atlas.costs.reshape(-1)
        inequalities[1:, :-1] = losses
        inequalities[1:, -1] = -1
        self.inequalities = csr_matrix(inequalities)
        self.inequality_targets = np.array([atlas.budget, 0, 0, 0, 0])
        rows, columns, coefficients, targets = [], [], [], []

        def add_row(indices, values, target=0):
            rows.extend([len(targets)] * len(indices))
            columns.extend(indices)
            coefficients.extend(values)
            targets.append(target)

        for vertex in range(atlas.vertices):
            add_row(list(range(4 * vertex, 4 * vertex + 4)), [1] * 4, 1)
        for edge, endpoints in enumerate(atlas.edges):
            pair_indices = np.arange(self.unary_count + 16 * edge, self.unary_count + 16 * edge + 16).reshape(4, 4)
            for position, vertex in enumerate(endpoints):
                for choice in range(4):
                    selected = pair_indices[choice] if position == 0 else pair_indices[:, choice]
                    add_row([4 * vertex + choice] + selected.tolist(), [-1] + [1] * 4)
        digits = np.indices((4, 4, 4, 4)).reshape(4, 256)
        for face, corners in enumerate(atlas.plaquettes):
            edges = [(2 * corners[0], 0, 1), (2 * corners[1] + 1, 1, 2),
                     (2 * corners[3], 3, 2), (2 * corners[0] + 1, 0, 3)]
            for edge, first_position, second_position in edges:
                for first, second in itertools.product(range(4), repeat=2):
                    selected = np.flatnonzero((digits[first_position] == first) &
                                              (digits[second_position] == second))
                    add_row([self.unary_count + 16 * edge + 4 * first + second] +
                            (self.face_offset + 256 * face + selected).tolist(), [-1] + [1] * 16)
        for scenario in range(4):
            selected_flux = atlas.flux[scenario].reshape(-1)
            selected = np.flatnonzero(np.abs(selected_flux) > 1e-12)
            add_row((self.face_offset + selected).tolist(), selected_flux[selected].tolist(),
                    2 * np.pi * atlas.targets[scenario])
        self.equalities = coo_matrix((coefficients, (rows, columns)),
                                    shape=(len(targets), self.variable_count)).tocsr()
        self.equality_targets = np.asarray(targets)
        self.digits = digits

    def solve(self, allowed, seconds):
        bounds = self.bounds.copy()
        bounds[:self.unary_count, 1] = allowed.reshape(-1)
        pair_allowed = allowed[self.atlas.edges[:, 0], :, None] & allowed[self.atlas.edges[:, 1], None, :]
        bounds[self.unary_count:self.face_offset, 1] *= pair_allowed.reshape(-1)
        face_allowed = np.ones((self.atlas.vertices, 256), dtype=bool)
        for position in range(4):
            face_allowed &= allowed[self.atlas.plaquettes[:, position, None], self.digits[position]]
        bounds[self.face_offset:-1, 1] *= face_allowed.reshape(-1)
        return linprog(self.objective, A_eq=self.equalities, b_eq=self.equality_targets,
                       A_ub=self.inequalities, b_ub=self.inequality_targets,
                       bounds=bounds, method='highs', options={'time_limit': seconds})


def rounded_candidates(atlas, probabilities):
    choices = np.argmax(probabilities, axis=1).astype(np.int32)
    fractional = np.flatnonzero(np.max(probabilities, axis=1) < 1 - 1e-6)
    supports = [np.flatnonzero(probabilities[vertex] > 1e-6) for vertex in fractional]
    count = 1
    for support in supports:
        count *= len(support)
        if count > 2048:
            return choices[None]
    candidates = np.tile(choices, (count, 1))
    if len(fractional):
        candidates[:, fractional] = np.asarray(list(itertools.product(*supports)))
    costs = atlas.costs[np.arange(atlas.vertices), candidates].sum(axis=1)
    return candidates[costs <= atlas.budget]


def refine(atlas, initial, seconds, polish):
    deadline = time.monotonic() + seconds
    best = np.asarray(initial, dtype=np.int32).copy()
    incumbent = atlas.score(best)['objective']
    model = Relaxation(atlas)
    allowed = model.bounds[:model.unary_count, 1].reshape(atlas.vertices, 4).astype(bool)
    queue = [(0.0, 0, allowed)]
    sequence = 0
    root_bound = 0.0
    nodes = 0
    interrupted = False
    while queue and time.monotonic() < deadline - 0.2:
        bound, _, allowed = heapq.heappop(queue)
        if bound >= incumbent - 1e-9:
            continue
        seconds_left = deadline - time.monotonic()
        result = model.solve(allowed, min(12.0 if nodes == 0 else 4.0, seconds_left))
        nodes += 1
        if result.status == 2:
            continue
        if not result.success:
            interrupted = True
            break
        bound = float(result.fun)
        if nodes == 1:
            root_bound = bound
        if bound >= incumbent - 1e-9:
            continue
        probabilities = np.clip(result.x[:model.unary_count].reshape(atlas.vertices, 4), 0, 1)
        candidates = rounded_candidates(atlas, probabilities)
        for batch_start in range(0, len(candidates), 128):
            batch = candidates[batch_start:batch_start + 128]
            values = atlas.evaluate_many(batch)
            objectives = np.where(values['feasible'], values['objective'], np.inf)
            selected = int(np.argmin(objectives))
            if objectives[selected] < incumbent - 1e-10:
                best = batch[selected].copy()
                best = polish(best, min(0.08, max(0.001, deadline - time.monotonic())))
                incumbent = atlas.score(best)['objective']
        if bound >= incumbent - 1e-9:
            continue
        reduced_cost = result.lower.marginals[:model.unary_count].reshape(atlas.vertices, 4)
        removable = (probabilities < 1e-7) & (reduced_cost > incumbent - bound + 1e-8)
        allowed = allowed & ~removable
        if np.any(~np.any(allowed, axis=1)):
            continue
        fractionality = np.minimum(probabilities, 1 - probabilities)
        fractionality[~allowed] = 0
        vertex, choice = np.unravel_index(np.argmax(fractionality), fractionality.shape)
        if fractionality[vertex, choice] < 1e-7:
            continue
        for selected in (True, False):
            child = allowed.copy()
            if selected:
                child[vertex] = False
                child[vertex, choice] = True
            else:
                child[vertex, choice] = False
            if np.any(~np.any(child, axis=1)):
                continue
            sequence += 1
            heapq.heappush(queue, (bound, sequence, child))
    if interrupted:
        lower_bound = root_bound
    elif queue:
        lower_bound = min(incumbent, min(item[0] for item in queue))
    else:
        lower_bound = incumbent
    if os.environ.get('ATLAS_DEBUG'):
        import sys
        print('LP nodes', nodes, 'lower bound', lower_bound, 'incumbent', incumbent, file=sys.stderr)
    return best, lower_bound
