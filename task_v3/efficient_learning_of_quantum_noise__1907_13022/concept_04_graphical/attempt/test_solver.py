import os

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"

import time
from itertools import combinations

import numpy as np
from scipy.special import gammaln, logsumexp

from solver import EliminationModel, learn_interactions, log_convolve, solve


def make_terms(size, generator):
    terms = {(node,): -generator.uniform(2, 9) for node in range(size)}
    for last in range(1, size):
        previous = range(max(0, last - 3), last)
        for first in previous:
            if generator.random() < 0.65:
                terms[(first, last)] = generator.uniform(-4, 5)
        for earlier in combinations(previous, 2):
            if generator.random() < 0.4:
                terms[earlier + (last,)] = generator.uniform(-4, 12)
    return terms


def queries(size, generator, amount=24):
    fixed = np.full((amount, size), -1, dtype=np.int8)
    count_mask = generator.integers(0, 2, (amount, size), dtype=np.int8)
    parity_mask = generator.integers(0, 2, (amount, size), dtype=np.int8)
    parity_value = np.full(amount, -1, dtype=np.int8)
    lower = np.zeros(amount, dtype=np.int64)
    upper = np.zeros(amount, dtype=np.int64)
    for query in range(amount):
        witness = generator.integers(0, 2, size, dtype=np.int8)
        witness[generator.integers(size)] = 1
        pinned = generator.random(size) < (1.0 if query % 11 == 0 else 0.25)
        fixed[query, pinned] = witness[pinned]
        if query % 5 == 0:
            count_mask[query] = 1
        elif query % 7 == 0:
            count_mask[query] = 0
        weight = int(witness @ count_mask[query])
        maximum = int(count_mask[query].sum())
        if query % 4 == 0:
            lower[query], upper[query] = 0, maximum
        elif query % 4 == 1:
            lower[query] = upper[query] = weight
        else:
            lower[query] = generator.integers(weight + 1)
            upper[query] = generator.integers(weight, maximum + 1)
        if query % 3:
            parity_value[query] = (witness @ parity_mask[query]) % 2
        if not np.any(fixed[query] == 1) and lower[query] == 0 and parity_value[query] != 1:
            fixed[query, np.flatnonzero(witness)[0]] = 1
    activity = generator.uniform(-16, 0, amount)
    activity[::3] = 0
    activity[1::3] = -16
    return dict(log_activity=activity, fixed=fixed, count_mask=count_mask,
                weight_lo=lower, weight_hi=upper, parity_mask=parity_mask,
                parity_value=parity_value, event_group=np.arange(amount, dtype=np.int8) % 3)


def dense_case(size, terms, generator):
    indices = np.arange(1 << size)
    states = ((indices[:, None] >> np.arange(size)) & 1).astype(np.int8)
    energies = np.zeros(indices.size)
    neighbors = [set() for _ in range(size)]
    for scope, value in terms.items():
        mask = sum(1 << node for node in scope)
        energies[(indices & mask) == mask] += value
        for node in scope:
            neighbors[node].update(set(scope) - {node})
    joint = np.exp(energies - logsumexp(energies))
    candidates = list(combinations(range(size), 2))
    generator.shuffle(candidates)
    for first, second in candidates:
        if len(neighbors[first]) < 7 and len(neighbors[second]) < 7:
            neighbors[first].add(second)
            neighbors[second].add(first)
    centers = generator.permutation(size)
    scope_nodes = np.full((size, 8), -1, dtype=np.int64)
    scope_size = []
    local_ptr = [0]
    local_probs = []
    for row, center in enumerate(centers):
        scope = generator.permutation([center] + sorted(neighbors[center]))
        scope_nodes[row, :len(scope)] = scope
        scope_size.append(len(scope))
        local_indices = states[:, scope] @ (1 << np.arange(len(scope)))
        probs = np.bincount(local_indices, weights=joint, minlength=1 << len(scope))
        local_probs.extend(probs)
        local_ptr.append(len(local_probs))
    data = dict(version=np.int64(1), n=np.int64(size), max_order=np.int64(3),
                centers=centers, scope_size=np.array(scope_size), scope_nodes=scope_nodes,
                local_ptr=np.array(local_ptr), local_probs=np.array(local_probs))
    data.update(queries(size, generator))
    expected = []
    for query, activity in enumerate(data["log_activity"]):
        valid = np.all((data["fixed"][query] < 0) | (states == data["fixed"][query]), axis=1)
        weights = states @ data["count_mask"][query]
        valid &= (weights >= data["weight_lo"][query]) & (weights <= data["weight_hi"][query])
        if data["parity_value"][query] >= 0:
            valid &= ((states @ data["parity_mask"][query]) % 2) == data["parity_value"][query]
        tilted = energies + activity * states.sum(axis=1)
        expected.append(logsumexp(tilted[valid]) - logsumexp(tilted))
    return data, np.array(expected)


def chain_transitions(size, terms):
    transition = np.zeros((size, 8, 2))
    for scope, value in terms.items():
        node = max(scope)
        for history in range(8):
            if all((history >> (node - earlier - 1)) & 1 for earlier in scope if earlier != node):
                transition[node, history, 1] += value
    return transition


def chain_observations(size, terms, generator):
    transition = chain_transitions(size, terms)
    forward = np.full((size + 1, 8), -np.inf)
    forward[0, 0] = 0
    for node in range(size):
        for history in range(8):
            for bit in range(2):
                destination = ((history << 1) | bit) & 7
                forward[node + 1, destination] = np.logaddexp(
                    forward[node + 1, destination], forward[node, history] + transition[node, history, bit]
                )
    backward = np.zeros((size + 1, 8))
    for node in range(size - 1, -1, -1):
        for history in range(8):
            backward[node, history] = np.logaddexp(
                transition[node, history, 0] + backward[node + 1, (history << 1) & 7],
                transition[node, history, 1] + backward[node + 1, ((history << 1) | 1) & 7],
            )
    normalizer = logsumexp(forward[-1])
    labels = generator.permutation(size)
    centers = generator.permutation(size)
    scope_nodes = np.full((size, 8), -1, dtype=np.int64)
    scope_size = []
    local_probs = []
    local_ptr = [0]
    for row, center in enumerate(centers):
        start, stop = max(0, center - 3), min(size, center + 4)
        nodes = list(range(start, stop))
        axis_order = generator.permutation(len(nodes))
        scope_nodes[row, :len(nodes)] = labels[np.array(nodes)[axis_order]]
        scope_size.append(len(nodes))
        table = np.zeros(1 << len(nodes))
        for assignment in range(1 << len(nodes)):
            score = []
            for previous in range(8):
                history = previous
                energy = forward[start, history]
                for offset, node in enumerate(nodes):
                    bit = (assignment >> offset) & 1
                    energy += transition[node, history, bit]
                    history = ((history << 1) | bit) & 7
                score.append(energy + backward[stop, history])
            index = sum(((assignment >> old_axis) & 1) << new_axis
                        for new_axis, old_axis in enumerate(axis_order))
            table[index] = np.exp(logsumexp(score) - normalizer)
        local_probs.extend(table / table.sum())
        local_ptr.append(len(local_probs))
    labeled_terms = {tuple(sorted(labels[list(scope)])): value for scope, value in terms.items()}
    data = dict(version=np.int64(1), n=np.int64(size), max_order=np.int64(3),
                centers=labels[centers], scope_size=np.array(scope_size), scope_nodes=scope_nodes,
                local_ptr=np.array(local_ptr), local_probs=np.array(local_probs))
    data.update(queries(size, generator))
    return data, labeled_terms, transition, labels


def chain_query(transition, activity, fixed, count_mask, lower, upper, parity_mask, parity_value):
    size = len(transition)
    count_size = int(count_mask.sum())
    distribution = np.full((8, count_size + 1, 2), -np.inf)
    distribution[0, 0, 0] = 0
    for node in range(size):
        updated = np.full_like(distribution, -np.inf)
        for history in range(8):
            for bit in range(2):
                if fixed[node] >= 0 and fixed[node] != bit:
                    continue
                shift = int(count_mask[node]) * bit
                parity_shift = int(parity_mask[node]) * bit
                destination = ((history << 1) | bit) & 7
                source = distribution[history, :count_size + 1 - shift]
                if parity_shift:
                    source = source[:, ::-1]
                target = updated[destination, shift:]
                np.logaddexp(target, source + transition[node, history, bit] + activity * bit, out=target)
        distribution = updated
    if parity_value >= 0:
        return logsumexp(distribution[:, lower:upper + 1, parity_value])
    return logsumexp(distribution[:, lower:upper + 1])


def test_small():
    generator = np.random.default_rng(618237)
    maximum = 0
    start = time.monotonic()
    for trial in range(60):
        size = int(generator.integers(8, 15))
        terms = make_terms(size, generator)
        labels = generator.permutation(size)
        terms = {tuple(sorted(labels[list(scope)])): value for scope, value in terms.items()}
        data, expected = dense_case(size, terms, generator)
        recovered = learn_interactions(data)
        assert set(terms) == set(recovered), (trial, set(terms) ^ set(recovered))
        coefficient_error = max(abs(value - recovered[scope]) for scope, value in terms.items())
        assert coefficient_error < 1e-10, coefficient_error
        predicted = solve(data)
        error = np.max(np.abs(predicted - expected))
        assert np.isfinite(predicted).all(), (trial, predicted)
        assert error < 1e-9, (trial, error, predicted, expected)
        maximum = max(maximum, error)
    print("Dense tests:", 60 * 24, "queries; max log error", maximum,
          "seconds", time.monotonic() - start, flush=True)


def test_large():
    generator = np.random.default_rng(817124)
    size = 120
    terms = make_terms(size, generator)
    start = time.monotonic()
    data, labeled_terms, transition, labels = chain_observations(size, terms, generator)
    data["fixed"][-1] = -1
    data["count_mask"][-1] = 1
    data["weight_lo"][-1] = 115
    data["weight_hi"][-1] = 120
    data["parity_value"][-1] = -1
    data["log_activity"][-1] = -16
    np.savez("large_case.npz", **data)
    print("Large data generated in", time.monotonic() - start, "seconds", flush=True)
    start = time.monotonic()
    predicted = solve(data)
    elapsed = time.monotonic() - start
    model = EliminationModel(size, labeled_terms)
    expected = []
    for query, activity in enumerate(data["log_activity"]):
        numerator = chain_query(
            transition, activity, data["fixed"][query, labels], data["count_mask"][query, labels],
            data["weight_lo"][query], data["weight_hi"][query],
            data["parity_mask"][query, labels], data["parity_value"][query],
        )
        denominator = chain_query(transition, activity, np.full(size, -1), np.zeros(size, dtype=int),
                                  0, 0, np.zeros(size, dtype=int), -1)
        assert abs(model.log_partition(activity) - denominator) < 1e-10
        expected.append(numerator - denominator)
    error = np.max(np.abs(predicted - expected))
    assert error < 1e-8, (error, predicted, expected)
    print("Large test: width", model.width, "24 queries; max log error", error,
          "solver seconds", elapsed, "rarest log probability", min(predicted), flush=True)


def test_convolution():
    generator = np.random.default_rng(8195)
    for trial in range(1000):
        first_length, second_length = generator.integers(1, 12, 2)
        first_parity, second_parity = generator.integers(1, 3, 2)
        limit = int(generator.integers(0, first_length + second_length))
        first = generator.uniform(-100, 100, (3, first_length, first_parity))
        second = generator.uniform(-100, 100, (3, second_length, second_parity))
        first[generator.random(first.shape) < 0.2] = -np.inf
        second[generator.random(second.shape) < 0.2] = -np.inf
        predicted = log_convolve(first, second, limit)
        expected = np.full_like(predicted, -np.inf)
        for first_index in range(first_length):
            for second_index in range(second_length):
                if first_index + second_index >= expected.shape[1]:
                    continue
                for first_channel in range(first_parity):
                    for second_channel in range(second_parity):
                        target = expected[:, first_index + second_index, first_channel ^ second_channel]
                        np.logaddexp(target, first[:, first_index, first_channel]
                                     + second[:, second_index, second_channel], out=target)
        assert np.allclose(predicted, expected, atol=1e-12, rtol=1e-14), trial
    print("Convolution tests: 1000 passed", flush=True)


def test_independent():
    size = 120
    field = -12.0
    model = EliminationModel(size, {(node,): field for node in range(size)})
    maximum = 0.0
    for activity in (0.0, -4.0, -16.0):
        for pinned_ones, pinned_zeros in ((0, 0), (20, 10), (30, 90)):
            fixed = np.full(size, -1, dtype=np.int8)
            fixed[:pinned_ones] = 1
            fixed[pinned_ones:pinned_ones + pinned_zeros] = 0
            free_count = size - pinned_ones - pinned_zeros
            for lower, upper in ((1, 120), (30, 90), (110, 120), (0, 120)):
                for parity_value in (-1, 0, 1):
                    weights = np.arange(max(pinned_ones, lower), min(size - pinned_zeros, upper) + 1)
                    if parity_value >= 0:
                        weights = weights[weights % 2 == parity_value]
                    if not weights.size:
                        continue
                    free_ones = weights - pinned_ones
                    log_choose = (gammaln(free_count + 1) - gammaln(free_ones + 1)
                                  - gammaln(free_count - free_ones + 1))
                    expected = logsumexp(log_choose + weights * (field + activity))
                    predicted = model.log_event_partition(activity, fixed, np.ones(size, dtype=np.int8),
                                                           lower, upper, np.ones(size, dtype=np.int8), parity_value)
                    error = abs(expected - predicted)
                    maximum = max(maximum, error)
                    assert error < 1e-9, (expected, predicted)
    print("Independent analytic tests: max log error", maximum, flush=True)


if __name__ == "__main__":
    test_convolution()
    test_independent()
    test_small()
    test_large()
