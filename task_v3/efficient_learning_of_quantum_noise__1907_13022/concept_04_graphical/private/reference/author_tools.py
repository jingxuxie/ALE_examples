import itertools

import numpy as np
from scipy.special import logsumexp


def model(family, num_variables, rng, region=0):
    field_offset = (0.0, 0.8, -0.55)[region]
    coefficients = {(node,): -float(rng.uniform(4.7, 5.9) + field_offset) for node in range(num_variables)}
    candidates = {node: set() for node in range(num_variables)}

    def envelope(scope):
        for first, second in itertools.combinations(scope, 2):
            candidates[first].add(second)
            candidates[second].add(first)

    def coupling(first, second):
        value = float(rng.uniform(1.2, 3.2) + (0.4 if region == 1 else 0.0))
        if rng.random() < 0.12:
            value = -float(rng.uniform(0.7, 1.8))
        coefficients[tuple(sorted((first, second)))] = value
        envelope((first, second))

    if family == "mediated_chain":
        for node in range(num_variables - 1):
            coupling(node, node + 1)
        for node in range(num_variables - 2):
            envelope((node, node + 2))
    elif family == "loop_ladder":
        if num_variables % 2:
            raise ValueError("Ladders need an even size")
        for cell in range(num_variables // 2):
            first, second = 2 * cell, 2 * cell + 1
            envelope((first, second))
            if rng.random() < 0.8:
                coupling(first, second)
            if cell:
                coupling(first - 2, first)
                coupling(second - 2, second)
                envelope((first - 2, second))
                envelope((second - 2, first))
    elif family == "branch_triples":
        if num_variables % 3:
            raise ValueError("Triple branches need a multiple of three")
        for cell in range(num_variables // 3):
            stem, first, second = 3 * cell, 3 * cell + 1, 3 * cell + 2
            envelope((stem, first, second))
            coefficients[(stem, first, second)] = float(rng.uniform(8.0, 10.5) + field_offset)
            for leaf in (first, second):
                if rng.random() < 0.55:
                    coefficients[(stem, leaf)] = float(rng.uniform(-1.2, 1.4))
            if rng.random() < 0.45:
                coefficients[(first, second)] = float(rng.uniform(-1.5, 0.8))
            if cell:
                coupling(stem - 3, stem)
                envelope((stem - 3, first))
                envelope((stem - 1, stem))
    else:
        raise ValueError(f"Unknown family: {family}")
    permutation = rng.permutation(num_variables)
    renamed = {tuple(sorted(int(permutation[node]) for node in scope)): value for scope, value in coefficients.items()}
    envelopes = {int(permutation[node]): sorted(int(permutation[other]) for other in neighbors) for node, neighbors in candidates.items()}
    return renamed, envelopes, [int(node) for node in permutation]


def local_marginal(coefficients, order, keep):
    factors = []
    for scope, coefficient in coefficients.items():
        values = np.zeros((2,) * len(scope))
        values[(1,) * len(scope)] = coefficient
        factors.append((scope, values))
    for node in order:
        if node in keep:
            continue
        involved = [(scope, values) for scope, values in factors if node in scope]
        factors = [(scope, values) for scope, values in factors if node not in scope]
        union = tuple(sorted(set().union(*(set(scope) for scope, values in involved))))
        summed = np.zeros((2,) * len(union))
        for scope, values in involved:
            summed += values.reshape(tuple(2 if member in scope else 1 for member in union))
        reduced_scope = tuple(member for member in union if member != node)
        factors.append((reduced_scope, logsumexp(summed, axis=union.index(node))))
    retained = tuple(sorted(keep))
    combined = np.zeros((2,) * len(retained))
    for scope, values in factors:
        combined += values.reshape(tuple(2 if member in scope else 1 for member in retained))
    combined = combined.transpose(tuple(retained.index(member) for member in keep))
    return np.exp(combined - logsumexp(combined)).ravel(order="F")


def observations(coefficients, candidates, order, rng):
    num_variables = len(order)
    centers = rng.permutation(num_variables)
    scopes = np.full((num_variables, 8), -1, dtype=np.int64)
    sizes, offsets, probabilities = [], [0], []
    for row, center in enumerate(centers):
        scope = [int(center)] + candidates[int(center)]
        rng.shuffle(scope)
        if len(scope) > 8:
            raise ValueError("Observation envelope too large")
        local = local_marginal(coefficients, order, scope)
        if not np.all(local > 0):
            raise ValueError("Nonpositive local input")
        scopes[row, :len(scope)] = scope
        sizes.append(len(scope))
        probabilities.extend(local)
        offsets.append(len(probabilities))
    return {
        "version": np.array(1, dtype=np.int64),
        "n": np.array(num_variables, dtype=np.int64),
        "max_order": np.array(3, dtype=np.int64),
        "centers": centers.astype(np.int64),
        "scope_nodes": scopes,
        "scope_size": np.asarray(sizes, dtype=np.int64),
        "local_ptr": np.asarray(offsets, dtype=np.int64),
        "local_probs": np.asarray(probabilities, dtype=np.float64),
    }


def queries(num_variables, order, rng, challenge=False):
    count = 18
    fixed = np.full((count, num_variables), -1, dtype=np.int8)
    count_mask = np.zeros((count, num_variables), dtype=np.int8)
    parity_mask = np.zeros((count, num_variables), dtype=np.int8)
    parity_value = np.full(count, -1, dtype=np.int8)
    lower = np.zeros(count, dtype=np.int64)
    upper = np.zeros(count, dtype=np.int64)
    activity = np.tile(np.array([0.0, -1.0, -3.0, -5.0, -8.0, -12.0]), 3)
    if challenge:
        activity[activity < 0] -= rng.uniform(0.3, 1.5, size=np.sum(activity < 0))
    for query in range(count):
        group, slot = divmod(query, 6)
        if group == 0:
            selected = rng.choice(num_variables, size=num_variables if slot % 2 == 0 else max(4, int(0.8 * num_variables)), replace=False)
            count_mask[query, selected] = 1
            lower[query] = max(1, int(len(selected) * (0.08, 0.15, 0.25, 0.45, 0.7, 0.92)[slot]))
            upper[query] = len(selected)
        elif group == 1:
            burst = min(num_variables - 2, max(2, int(num_variables * (0.04, 0.07, 0.12, 0.2, 0.32, 0.55)[slot])))
            start = int(rng.integers(0, num_variables - burst + 1))
            fixed[query, order[start:start + burst]] = 1
            outside = [node for node in range(num_variables) if fixed[query, node] == -1]
            fixed[query, rng.choice(outside, min(7, len(outside)), replace=False)] = 0
            upper[query] = 0
        else:
            selected = rng.choice(num_variables, size=max(4, int(0.85 * num_variables)), replace=False)
            count_mask[query, selected] = 1
            lower[query] = max(1, int(len(selected) * (0.08, 0.13, 0.23, 0.38, 0.57, 0.85)[slot]))
            upper[query] = min(len(selected), lower[query] + (2 if slot % 2 else len(selected)))
            parity_mask[query, rng.choice(num_variables, size=max(2, num_variables // 3), replace=False)] = 1
            parity_value[query] = int(rng.integers(2))
    return {
        "log_activity": activity,
        "fixed": fixed,
        "count_mask": count_mask,
        "weight_lo": lower,
        "weight_hi": upper,
        "parity_mask": parity_mask,
        "parity_value": parity_value,
        "event_group": np.repeat(np.arange(3, dtype=np.int8), 6),
    }


def frontier_plan(coefficients, order):
    positions = {node: position for position, node in enumerate(order)}
    closing = [[] for node in order]
    last_use = dict(positions)
    for scope, coefficient in coefficients.items():
        last = max(positions[node] for node in scope)
        closing[last].append((scope, coefficient))
        for node in scope:
            last_use[node] = max(last_use[node], last)
    frontier, plan = [], []
    for position, node in enumerate(order):
        combined = frontier + [node]
        following = [member for member in combined if last_use[member] > position]
        transitions = []
        for state in range(2 ** len(frontier)):
            assigned = {member: state >> axis & 1 for axis, member in enumerate(frontier)}
            for value in (0, 1):
                assigned[node] = value
                energy = sum(coefficient for scope, coefficient in closing[position] if all(assigned[member] for member in scope))
                target = sum(assigned[member] << axis for axis, member in enumerate(following))
                transitions.append((state, value, target, energy))
        plan.append((node, 2 ** len(following), transitions))
        frontier = following
    return plan


def frontier_contract(plan, activity, fixed, counted, parity, cap):
    states = np.array([[[0.0, -np.inf]]])
    for node, boundary_size, transitions in plan:
        length = min(cap + 1, states.shape[1] + int(counted[node]))
        updated = np.full((boundary_size, length, 2), -np.inf)
        for source, value, target, energy in transitions:
            if fixed[node] not in (-1, value):
                continue
            shift = int(counted[node]) * value
            available = min(states.shape[1], length - shift)
            if available <= 0:
                continue
            contribution = states[source, :available] + energy + activity * value
            if int(parity[node]) * value:
                contribution = contribution[:, ::-1]
            destination = updated[target, shift:shift + available]
            np.logaddexp(destination, contribution, out=destination)
        states = updated
    return states[0]


def oracle(data, coefficients, order):
    num_variables = int(data["n"])
    plan = frontier_plan(coefficients, order)
    free = np.full(num_variables, -1, dtype=np.int8)
    zeros = np.zeros(num_variables, dtype=np.int8)
    normalizers, predictions = {}, []
    for query, activity in enumerate(data["log_activity"]):
        activity = float(activity)
        if activity not in normalizers:
            normalizers[activity] = float(frontier_contract(plan, activity, free, zeros, zeros, 0)[0, 0])
        lower, upper = int(data["weight_lo"][query]), int(data["weight_hi"][query])
        parity = int(data["parity_value"][query])
        mask = data["parity_mask"][query] if parity != -1 else zeros
        result = frontier_contract(plan, activity, data["fixed"][query], data["count_mask"][query], mask, upper)
        selected = result[lower:upper + 1] if parity == -1 else result[lower:upper + 1, parity]
        predictions.append(float(logsumexp(selected) - normalizers[activity]))
    return np.asarray(predictions)


def exhaustive(data, coefficients):
    num_variables = int(data["n"])
    if num_variables > 18:
        raise ValueError("Exhaustive check is only for tiny systems")
    patterns = (np.arange(1 << num_variables, dtype=np.int64)[:, None] >> np.arange(num_variables)) & 1
    energy = np.zeros(patterns.shape[0])
    for scope, coefficient in coefficients.items():
        energy += coefficient * np.prod(patterns[:, scope], axis=1)
    answers = []
    for query, activity in enumerate(data["log_activity"]):
        tilted = energy + activity * patterns.sum(axis=1)
        valid = np.all((data["fixed"][query] == -1) | (patterns == data["fixed"][query]), axis=1)
        weights = patterns @ data["count_mask"][query]
        valid &= (weights >= data["weight_lo"][query]) & (weights <= data["weight_hi"][query])
        if data["parity_value"][query] != -1:
            valid &= (patterns @ data["parity_mask"][query]) % 2 == data["parity_value"][query]
        answers.append(float(logsumexp(tilted[valid]) - logsumexp(tilted)))
    return np.asarray(answers), np.exp(energy - logsumexp(energy))


def case(family, num_variables, seed, region=0, challenge=False):
    rng = np.random.default_rng(seed)
    coefficients, candidates, order = model(family, num_variables, rng, region)
    data = observations(coefficients, candidates, order, rng)
    data.update(queries(num_variables, order, rng, challenge))
    return data, coefficients, order


def save_model(path, coefficients, order):
    nodes = np.full((len(coefficients), 3), -1, dtype=np.int64)
    sizes, values = [], []
    for row, (scope, coefficient) in enumerate(coefficients.items()):
        nodes[row, :len(scope)] = scope
        sizes.append(len(scope))
        values.append(coefficient)
    np.savez_compressed(path, nodes=nodes, sizes=np.asarray(sizes), coefficients=np.asarray(values), order=np.asarray(order))


def load_model(path):
    with np.load(path, allow_pickle=False) as archive:
        coefficients = {tuple(int(node) for node in archive["nodes"][row, :size]): float(archive["coefficients"][row]) for row, size in enumerate(archive["sizes"])}
        return coefficients, list(archive["order"])
