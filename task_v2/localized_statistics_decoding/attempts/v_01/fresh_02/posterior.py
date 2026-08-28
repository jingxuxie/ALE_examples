import math

import numpy as np


def parity(values):
    values = np.array(values, dtype=np.uint64, copy=True)
    for shift in (32, 16, 8, 4, 2, 1):
        values ^= values >> np.uint64(shift)
    return (values & np.uint64(1)).astype(np.int8)


def combinations(generators):
    result = np.empty(1 << len(generators), dtype=np.uint64)
    result[0] = 0
    for index, generator in enumerate(generators):
        extent = 1 << index
        result[extent:2 * extent] = result[:extent] ^ np.uint64(generator)
    return result


class LocalModel:
    def __init__(self, faults, internal, boundary, boundary_faults, observed, signs):
        observed_set = set(observed)
        self.active = [index for index in internal if observed_set.intersection(faults[index]['detectors'])]
        self.inactive = [index for index in internal if index not in self.active]
        self.signs = signs
        self.count = len(self.active)
        self.boundary_count = len(boundary)
        self.channel_count = signs.shape[0]
        self.active_signs = signs[:, self.active]
        self.character_masks = np.array([sum(1 << position for position, sign in enumerate(row) if sign < 0)
                                         for row in self.active_signs], dtype=np.uint64)
        rows = []
        for position, detector in enumerate(observed):
            row = sum(1 << column for column, index in enumerate(self.active)
                      if detector in faults[index]['detectors'])
            row |= sum(1 << (self.count + column) for column, variable in enumerate(boundary)
                       if detector in faults[boundary_faults[variable]]['detectors'])
            row |= 1 << (self.count + self.boundary_count + position)
            rows.append(row)
        self.pivots = []
        pivot_row = 0
        for column in range(self.count):
            candidate = next((index for index in range(pivot_row, len(rows))
                              if (rows[index] >> column) & 1), None)
            if candidate is None:
                continue
            rows[pivot_row], rows[candidate] = rows[candidate], rows[pivot_row]
            for target in range(len(rows)):
                if target != pivot_row and ((rows[target] >> column) & 1):
                    rows[target] ^= rows[pivot_row]
            self.pivots.append(column)
            pivot_row += 1
        self.rank = pivot_row
        self.rows = rows[:pivot_row]
        self.constraints = rows[pivot_row:]
        self.free = [column for column in range(self.count) if column not in self.pivots]
        self.generators = [((1 << column) | sum(1 << pivot for pivot, row in zip(self.pivots, self.rows)
                                               if (row >> column) & 1)) for column in self.free]
        self.coordinates = [sum(1 << position for position, row in enumerate(self.rows)
                                if (row >> column) & 1) for column in range(self.count)]
        self.boundary_values = np.arange(1 << self.boundary_count, dtype=np.uint64)
        self.boundary_mask = (1 << self.boundary_count) - 1
        self.source_shift = self.count + self.boundary_count

    def evaluate(self, syndrome, probabilities):
        valid = np.ones(len(self.boundary_values), dtype=bool)
        offsets = np.zeros(len(self.boundary_values), dtype=np.uint64)
        targets = np.zeros(len(self.boundary_values), dtype=np.uint64)
        for position, (pivot, row) in enumerate(zip(self.pivots, self.rows)):
            constant = ((row >> self.source_shift) & syndrome).bit_count() & 1
            values = parity(self.boundary_values & np.uint64((row >> self.count) & self.boundary_mask)) ^ constant
            offsets |= values.astype(np.uint64) << np.uint64(pivot)
            targets |= values.astype(np.uint64) << np.uint64(position)
        for row in self.constraints:
            constant = ((row >> self.source_shift) & syndrome).bit_count() & 1
            valid &= parity(self.boundary_values & np.uint64((row >> self.count) & self.boundary_mask)) == constant
        result = np.zeros((self.channel_count, len(valid)))
        if not valid.any():
            return result, 0.0
        unique, inverse = np.unique(offsets[valid], return_inverse=True)
        nullity = len(self.free)
        primal_work = len(unique) * (1 << nullity) * (self.count + self.channel_count)
        dual_work = (1 << self.rank) * (self.rank + self.channel_count * (nullity + 1))
        if self.rank <= 19 and dual_work < primal_work:
            distribution, log_scale = self.dynamic(probabilities)
            result[:, valid] = distribution[:, targets[valid].astype(np.intp)]
        else:
            values, log_scale = self.enumerate(unique, probabilities)
            result[:, valid] = values[:, inverse]
        for fault_index in self.inactive:
            rate = probabilities[fault_index]
            result *= (1.0 - rate + rate * self.signs[:, fault_index, None])
        return result, log_scale

    def enumerate(self, offsets, probabilities):
        vectors = combinations(self.generators)
        character_signs = 1.0 - 2.0 * parity(self.character_masks[:, None] & vectors[None, :])
        result = np.zeros((self.channel_count, len(offsets)))
        log_scale = -np.inf
        block_size = max(1, (1 << 19) // len(vectors))
        with np.errstate(divide='ignore'):
            log_rates = np.log(probabilities[self.active])
            log_complements = np.log1p(-probabilities[self.active])
        for start in range(0, len(offsets), block_size):
            selected = offsets[start:start + block_size]
            assignments = selected[:, None] ^ vectors[None, :]
            log_weights = np.zeros(assignments.shape)
            for column in range(self.count):
                log_weights += np.where((assignments >> np.uint64(column)) & np.uint64(1),
                                        log_rates[column], log_complements[column])
            maximum = float(log_weights.max())
            if not math.isfinite(maximum):
                continue
            weights = np.exp(log_weights - maximum)
            values = character_signs @ weights.T
            values *= 1.0 - 2.0 * parity(self.character_masks[:, None] & selected[None, :])
            if maximum > log_scale:
                if math.isfinite(log_scale):
                    result *= math.exp(log_scale - maximum)
                log_scale = maximum
            result[:, start:start + len(selected)] = values * math.exp(maximum - log_scale)
        return result, log_scale if math.isfinite(log_scale) else 0.0

    def dynamic(self, probabilities):
        states = np.arange(1 << self.rank, dtype=np.uint64)
        log_weights = np.zeros(len(states))
        with np.errstate(divide='ignore'):
            for position, pivot in enumerate(self.pivots):
                rate = probabilities[self.active[pivot]]
                log_weights += np.where((states >> np.uint64(position)) & np.uint64(1),
                                        np.log(rate), np.log1p(-rate))
        log_scale = float(log_weights.max())
        weights = np.exp(log_weights - log_scale)
        pivot_masks = np.array([sum(1 << position for position, pivot in enumerate(self.pivots)
                                    if row[pivot] < 0) for row in self.active_signs], dtype=np.uint64)
        distribution = weights[None, :] * (1.0 - 2.0 * parity(pivot_masks[:, None] & states[None, :]))
        for column in self.free:
            rate = probabilities[self.active[column]]
            if rate == 0.0:
                continue
            permutation = (states ^ np.uint64(self.coordinates[column])).astype(np.intp)
            distribution = ((1.0 - rate) * distribution
                            + rate * self.active_signs[:, column, None] * distribution[:, permutation])
        return distribution, log_scale


def contraction_plan(boundaries):
    region_count = len(boundaries)
    if region_count == 0:
        return None, 0
    full = (1 << region_count) - 1
    scopes = [sum(1 << variable for variable in scope) for scope in boundaries]
    owners = {}
    for region, scope in enumerate(boundaries):
        for variable in scope:
            owners[variable] = owners.get(variable, 0) | (1 << region)
    cuts = [0] * (full + 1)
    costs = [math.inf] * (full + 1)
    trees = [None] * (full + 1)
    widths = [0] * (full + 1)
    for subset in range(1, full + 1):
        cuts[subset] = sum(1 << variable for variable, support in owners.items()
                           if support & subset and support & (full ^ subset))
        if subset & (subset - 1) == 0:
            region = subset.bit_length() - 1
            costs[subset] = 0
            trees[subset] = region
            widths[subset] = scopes[region].bit_count()
            continue
        smallest = subset & -subset
        left = (subset - 1) & subset
        while left:
            right = subset ^ left
            if right and left & smallest:
                width = max(widths[left], widths[right], cuts[subset].bit_count())
                cost = costs[left] + costs[right] + (1 << (cuts[left] | cuts[right]).bit_count())
                if (cost, width) < (costs[subset], widths[subset]):
                    costs[subset] = cost
                    widths[subset] = width
                    trees[subset] = (trees[left], trees[right], cuts[subset])
            left = (left - 1) & subset
    return trees[full], widths[full]


def merge(left, right, retained):
    left_scope, left_values, left_scale = left
    right_scope, right_values, right_scale = right
    common = set(left_scope).intersection(right_scope)
    kept = [variable for variable in left_scope if variable in common and (retained >> variable) & 1]
    summed = [variable for variable in left_scope if variable in common and variable not in kept]
    left_only = [variable for variable in left_scope if variable not in common]
    right_only = [variable for variable in right_scope if variable not in common]
    left_order = kept + left_only + summed
    right_order = kept + summed + right_only
    left_values = left_values.transpose([0] + [1 + left_scope.index(variable) for variable in left_order])
    right_values = right_values.transpose([0] + [1 + right_scope.index(variable) for variable in right_order])
    channels = left_values.shape[0]
    left_values = left_values.reshape(channels, 1 << len(kept), 1 << len(left_only), 1 << len(summed))
    right_values = right_values.reshape(channels, 1 << len(kept), 1 << len(summed), 1 << len(right_only))
    values = np.matmul(left_values, right_values)
    scope = tuple(kept + left_only + right_only)
    values = values.reshape((channels,) + (2,) * len(scope))
    maximum = float(np.max(np.abs(values)))
    log_scale = left_scale + right_scale
    if maximum > 0.0:
        values /= maximum
        log_scale += math.log(maximum)
    return scope, values, log_scale


def contract(factors, plan, width, channel_count):
    chunk_size = max(1, min(channel_count, (1 << 22) // (1 << width)))
    chunks = []

    def evaluate(tree, start, end):
        if isinstance(tree, int):
            scope, values, scale = factors[tree]
            return scope, values[start:end], scale
        left_tree, right_tree, retained = tree
        left = evaluate(left_tree, start, end)
        right = evaluate(right_tree, start, end)
        return merge(left, right, retained)

    for start in range(0, channel_count, chunk_size):
        scope, values, scale = evaluate(plan, start, min(start + chunk_size, channel_count))
        chunks.append((values.reshape(-1), scale))
    evidence = float(chunks[0][0][0])
    if evidence <= 0.0:
        return -np.inf, np.zeros(channel_count)
    log_evidence = math.log(evidence) + chunks[0][1]
    moments = []
    for values, scale in chunks:
        nonzero = values != 0
        normalized = np.zeros_like(values)
        normalized[nonzero] = np.sign(values[nonzero]) * np.exp(np.minimum(0.0,
                                            np.log(np.abs(values[nonzero])) + scale - log_evidence))
        moments.extend(normalized.tolist())
    return log_evidence, np.asarray(moments)
