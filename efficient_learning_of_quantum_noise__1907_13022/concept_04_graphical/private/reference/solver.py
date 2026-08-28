import itertools
import sys

import numpy as np
from scipy.special import logsumexp


def marginal(table, axes):
    axes = tuple(axes)
    removed = tuple(axis for axis in range(table.ndim) if axis not in axes)
    reduced = table.sum(axis=removed)
    retained = sorted(axes)
    return reduced.transpose(tuple(retained.index(axis) for axis in axes))


def fixed_cmi(table, first, second, given):
    first, second, given = tuple(first), tuple(second), tuple(given)
    xsize, ysize, zsize = 2 ** len(first), 2 ** len(second), 2 ** len(given)
    joint_xyz = marginal(table, first + second + given).reshape(xsize * ysize, zsize, order="F")
    joint_xz = marginal(table, first + given).reshape(xsize, zsize, order="F")
    joint_yz = marginal(table, second + given).reshape(ysize, zsize, order="F")
    joint_z = marginal(table, given).reshape(zsize, order="F")
    stride = joint_xz.shape[0]
    total = 0.0
    for second_value in range(ysize):
        for first_value in range(xsize):
            weights = joint_xyz[stride * second_value + first_value]
            positive = weights > 0
            ratio_log = (
                np.log2(joint_z[positive]) + np.log2(weights[positive])
                - np.log2(joint_xz[first_value, positive])
                - np.log2(joint_yz[second_value, positive])
            )
            total += float(weights[positive] @ ratio_log)
    return total


def tables_from_data(data):
    for row, center in enumerate(data["centers"]):
        size = int(data["scope_size"][row])
        scope = tuple(int(value) for value in data["scope_nodes"][row, :size])
        start, stop = data["local_ptr"][row:row + 2]
        table = data["local_probs"][start:stop].reshape((2,) * size, order="F")
        yield int(center), scope, table


def learn(data, pair_only=False):
    observations = {}
    for center, scope, table in tables_from_data(data):
        center_axis = scope.index(center)
        candidates = [axis for axis in range(len(scope)) if axis != center_axis]
        active = []
        for start in range(0, len(candidates), 2):
            group = candidates[start:start + 2]
            given = [axis for axis in candidates if axis not in group]
            if fixed_cmi(table, (center_axis,), group, given) > 1e-13:
                for axis in group:
                    rest = [other for other in candidates if other != axis]
                    if fixed_cmi(table, (center_axis,), (axis,), rest) > 1e-13:
                        active.append(axis)
        reduced = marginal(table, (center_axis,) + tuple(active))
        coefficients = (np.log(reduced[1]) - np.log(reduced[0])).ravel(order="F").copy()
        for position in range(len(active)):
            step = 1 << position
            for start in range(0, coefficients.size, 2 * step):
                coefficients[start + step:start + 2 * step] -= coefficients[start:start + step]
        for subset, coefficient in enumerate(coefficients):
            members = [center] + [scope[axis] for position, axis in enumerate(active) if subset >> position & 1]
            if len(members) > int(data["max_order"]) or (pair_only and len(members) > 2):
                continue
            key = tuple(sorted(members))
            observations.setdefault(key, []).append(float(coefficient))
    learned = {}
    for scope, values in observations.items():
        coefficient = float(np.mean(values))
        if abs(coefficient) > 1e-7:
            learned[scope] = coefficient
    return learned


def canonical_factors(coefficients):
    factors = []
    for scope, coefficient in coefficients.items():
        table = np.zeros((2,) * len(scope))
        table[(1,) * len(scope)] = coefficient
        factors.append((scope, table))
    return factors


def elimination_order(num_variables, factors):
    graph = {node: set() for node in range(num_variables)}
    for scope, table in factors:
        for first, second in itertools.combinations(scope, 2):
            graph[first].add(second)
            graph[second].add(first)
    order = []
    while graph:
        def priority(node):
            neighbors = graph[node]
            missing = sum(second not in graph[first] for first, second in itertools.combinations(neighbors, 2))
            return missing, len(neighbors), node
        node = min(graph, key=priority)
        neighbors = graph[node]
        for first, second in itertools.combinations(neighbors, 2):
            graph[first].add(second)
            graph[second].add(first)
        for neighbor in neighbors:
            graph[neighbor].remove(node)
        del graph[node]
        order.append(node)
    return order


def align(scope, table, union):
    shape = tuple(2 if node in scope else 1 for node in union) + table.shape[len(scope):]
    return table.reshape(shape)


def multiply(first, second, cap):
    first_scope, first_table = first
    second_scope, second_table = second
    scope = tuple(sorted(set(first_scope) | set(second_scope)))
    left = align(first_scope, first_table, scope)
    right = align(second_scope, second_table, scope)
    if left.shape[-2] > right.shape[-2]:
        left, right = right, left
    degree = min(cap + 1, left.shape[-2] + right.shape[-2] - 1)
    result = np.full((2,) * len(scope) + (degree, 2), -np.inf)
    for count in range(min(left.shape[-2], degree)):
        available = min(right.shape[-2], degree - count)
        for parity in range(2):
            contribution = left[..., count, parity][..., None, None] + right[..., :available, :]
            if parity:
                contribution = contribution[..., ::-1]
            target = result[..., count:count + available, :]
            np.logaddexp(target, contribution, out=target)
    return scope, result


def contract(num_variables, factors, order, log_activity, fixed, count_mask, parity_mask, cap):
    positions = {node: position for position, node in enumerate(order)}
    buckets = [[] for node in order]
    for scope, values in factors:
        table = np.full(values.shape + (1, 2), -np.inf)
        table[..., 0, 0] = values
        buckets[min(positions[node] for node in scope)].append((scope, table))
    for node in range(num_variables):
        counted = int(count_mask[node])
        table = np.full((2, min(cap, counted) + 1, 2), -np.inf)
        for value in (0, 1):
            if fixed[node] not in (-1, value) or counted * value > cap:
                continue
            table[value, counted * value, int(parity_mask[node]) * value] = log_activity * value
        buckets[positions[node]].append(((node,), table))
    final = ((), np.array([[0.0, -np.inf]]))
    for position, node in enumerate(order):
        pending = sorted(buckets[position], key=lambda factor: factor[1].shape[-2])
        combined = pending[0]
        for factor in pending[1:]:
            combined = multiply(combined, factor, cap)
        scope, table = combined
        reduced_scope = tuple(member for member in scope if member != node)
        reduced = (reduced_scope, np.logaddexp.reduce(table, axis=scope.index(node)))
        if reduced_scope:
            buckets[min(positions[member] for member in reduced_scope)].append(reduced)
        else:
            final = multiply(final, reduced, cap)
    return final[1]


def solve_factors(data, factors, normalize=True):
    num_variables = int(data["n"])
    order = elimination_order(num_variables, factors)
    free = np.full(num_variables, -1, dtype=np.int8)
    zeros = np.zeros(num_variables, dtype=np.int8)
    normalizers = {}
    predictions = []
    for query, activity in enumerate(data["log_activity"]):
        activity = float(activity)
        if activity not in normalizers:
            normalizers[activity] = float(contract(num_variables, factors, order, activity, free, zeros, zeros, 0)[0, 0])
        parity = int(data["parity_value"][query])
        parity_mask = data["parity_mask"][query] if parity != -1 else zeros
        lower, upper = int(data["weight_lo"][query]), int(data["weight_hi"][query])
        result = contract(num_variables, factors, order, activity, data["fixed"][query], data["count_mask"][query], parity_mask, upper)
        selected = result[lower:upper + 1] if parity == -1 else result[lower:upper + 1, parity]
        prediction = float(logsumexp(selected))
        if normalize:
            prediction -= normalizers[activity]
        predictions.append(min(0.0, prediction) if normalize else prediction)
    return np.asarray(predictions)


def solve(data):
    return solve_factors(data, canonical_factors(learn(data)))


if __name__ == "__main__":
    with np.load(sys.argv[1], allow_pickle=False) as archive:
        data = dict(archive)
    np.savez(sys.argv[2], log_event=solve(data))
