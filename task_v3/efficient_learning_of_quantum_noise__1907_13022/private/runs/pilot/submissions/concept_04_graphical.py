import os

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

import sys
from collections import defaultdict
from itertools import combinations

import numpy as np


def learn_interactions(data):
    estimates = defaultdict(list)
    for row, center_value in enumerate(data["centers"]):
        center = int(center_value)
        size = int(data["scope_size"][row])
        scope = [int(node) for node in data["scope_nodes"][row, :size]]
        center_axis = scope.index(center)
        start, stop = data["local_ptr"][row:row + 2]
        table = data["local_probs"][start:stop].reshape((2,) * size, order="F")
        coefficients = (
            np.log(np.take(table, 1, axis=center_axis))
            - np.log(np.take(table, 0, axis=center_axis))
        ).ravel(order="F")
        neighbors = [node for node in scope if node != center]
        stride = 1
        while stride < coefficients.size:
            blocks = coefficients.reshape(-1, 2, stride)
            lower = blocks[:, 0, :].copy()
            upper = blocks[:, 1, :].copy()
            blocks[:, 0, :] = (lower + upper) * 0.5
            blocks[:, 1, :] = (upper - lower) * 0.5
            stride *= 2
        linear = np.array([coefficients[1 << axis] for axis in range(size - 1)])
        intercept = coefficients[0] - linear.sum()
        for first, second in combinations(range(size - 1), 2):
            coefficient = coefficients[(1 << first) | (1 << second)]
            intercept += coefficient
            linear[first] -= coefficient
            linear[second] -= coefficient
            interaction = tuple(sorted((center, neighbors[first], neighbors[second])))
            estimates[interaction].append(4.0 * coefficient)
        estimates[(center,)].append(float(intercept))
        for axis, neighbor in enumerate(neighbors):
            estimates[tuple(sorted((center, neighbor)))].append(2.0 * linear[axis])
    interactions = {}
    for scope, values in estimates.items():
        coefficient = float(np.mean(values))
        if len(scope) == 1 or abs(coefficient) > 1.0e-10:
            interactions[scope] = coefficient
    return interactions


def elimination_order(adjacency, mode=0, seed=0):
    graph = [set(neighbors) for neighbors in adjacency]
    remaining = set(range(len(graph)))
    generator = np.random.default_rng(seed)
    priorities = generator.random(len(graph)) if seed else np.arange(len(graph))
    order = []
    width = 0
    cost = 0
    while remaining:
        best_key = None
        best_node = None
        for node in remaining:
            neighbors = graph[node]
            degree = len(neighbors)
            fill = sum(len(neighbors - graph[neighbor]) - 1 for neighbor in neighbors) // 2
            primary = (fill, degree) if mode == 0 else (degree, fill)
            key = primary + (sum(len(graph[neighbor]) for neighbor in neighbors), priorities[node])
            if best_key is None or key < best_key:
                best_key = key
                best_node = node
        neighbors = graph[best_node]
        width = max(width, len(neighbors))
        cost += 1 << len(neighbors)
        for neighbor in neighbors:
            graph[neighbor].update(neighbors - {neighbor})
            graph[neighbor].discard(best_node)
        remaining.remove(best_node)
        graph[best_node] = set()
        order.append(best_node)
    return order, width, cost


class EliminationModel:
    def __init__(self, size, interactions):
        adjacency = [set() for _ in range(size)]
        for scope in interactions:
            for node in scope:
                adjacency[node].update(other for other in scope if other != node)
        order, width, cost = elimination_order(adjacency)
        if width > 3:
            for trial in range(10):
                candidate, candidate_width, candidate_cost = elimination_order(
                    adjacency, mode=trial % 2, seed=trial + 1
                )
                if (candidate_width, candidate_cost) < (width, cost):
                    order, width, cost = candidate, candidate_width, candidate_cost
                if width <= 3:
                    break
        self.size = size
        self.order = order
        self.width = width
        self.rank = {node: index for index, node in enumerate(order)}
        self.bags = []
        self.children = [[] for _ in order]
        self.roots = []
        graph = [set(neighbors) for neighbors in adjacency]
        for node in order:
            neighbors = graph[node]
            self.bags.append((node,) + tuple(sorted(neighbors, key=self.rank.get)))
            for neighbor in neighbors:
                graph[neighbor].update(neighbors - {neighbor})
                graph[neighbor].discard(node)
            graph[node] = set()
        self.potentials = [np.zeros(1 << len(bag)) for bag in self.bags]
        for scope, coefficient in interactions.items():
            owner = min(self.rank[node] for node in scope)
            bag = self.bags[owner]
            pattern = sum(1 << bag.index(node) for node in scope)
            states = np.arange(self.potentials[owner].size)
            self.potentials[owner][(states & pattern) == pattern] += coefficient
        for child, bag in enumerate(self.bags):
            if len(bag) == 1:
                self.roots.append(child)
                continue
            parent = self.rank[bag[1]]
            parent_bag = self.bags[parent]
            states = np.arange(1 << len(parent_bag))
            mapping = np.zeros(states.size, dtype=np.intp)
            for axis, node in enumerate(bag[1:]):
                mapping |= ((states >> parent_bag.index(node)) & 1) << axis
            self.children[parent].append((child, mapping))

    def log_partition(self, activity):
        messages = [None] * self.size
        for index, potential in enumerate(self.potentials):
            values = potential.copy()
            values[1::2] += activity
            for child, mapping in self.children[index]:
                values += messages[child][mapping]
                messages[child] = None
            messages[index] = np.logaddexp(values[::2], values[1::2])
        return sum(float(messages[root][0]) for root in self.roots)

    def log_event_partition(self, activity, fixed, count_mask, lower, upper,
                            parity_mask, parity_value):
        free = fixed < 0
        fixed_ones = fixed == 1
        fixed_count = int(np.sum(count_mask[fixed_ones]))
        counted = (count_mask != 0) & free
        count_size = int(np.sum(counted))
        lower = max(0, int(lower) - fixed_count)
        upper = min(count_size, int(upper) - fixed_count)
        complement = False
        if lower == 0 and upper == count_size:
            counted = np.zeros(self.size, dtype=bool)
            upper = 0
        elif upper > count_size - lower:
            lower, upper = count_size - upper, count_size - lower
            complement = True
        if parity_value >= 0:
            parity_value = int(parity_value) ^ (int(np.sum(parity_mask[fixed_ones])) & 1)
            parity = (parity_mask != 0) & free
            if not np.any(parity) and parity_value == 0:
                parity_value = -1
        else:
            parity = np.zeros(self.size, dtype=bool)
        messages = [None] * self.size
        for index, node in enumerate(self.order):
            values = None
            for child, mapping in self.children[index]:
                incoming = messages[child][mapping]
                messages[child] = None
                values = incoming if values is None else log_convolve(values, incoming, upper)
            if values is None:
                values = np.zeros((self.potentials[index].size, 1, 1))
            if fixed[node] >= 0:
                branch = int(fixed[node])
                result = values[branch::2] + self.potentials[index][branch::2, None, None]
                if branch:
                    result += activity
                messages[index] = result
                continue
            zero = values[::2] + self.potentials[index][::2, None, None]
            one = values[1::2] + self.potentials[index][1::2, None, None] + activity
            if not counted[node] and not parity[node]:
                messages[index] = np.logaddexp(zero, one)
                continue
            length = min(upper + 1, values.shape[1] + int(counted[node]))
            parity_size = 2 if parity[node] else values.shape[2]
            result = np.full((zero.shape[0], length, parity_size), -np.inf)
            for branch, contribution in enumerate((zero, one)):
                shift = int(counted[node] and (branch == 0 if complement else branch == 1))
                available = min(contribution.shape[1], length - shift)
                if available <= 0:
                    continue
                parity_shift = int(parity[node] and branch == 1)
                if contribution.shape[2] == parity_size:
                    source = contribution[:, :available, ::-1] if parity_shift else contribution[:, :available]
                    target = result[:, shift:shift + available]
                else:
                    source = contribution[:, :available, 0]
                    target = result[:, shift:shift + available, parity_shift]
                np.logaddexp(target, source, out=target)
            messages[index] = result
        total = None
        for root in self.roots:
            total = messages[root] if total is None else log_convolve(total, messages[root], upper)
        if parity_value < 0:
            selected = total[0, lower:upper + 1, :]
        elif parity_value < total.shape[2]:
            selected = total[0, lower:upper + 1, parity_value]
        else:
            return -np.inf
        return float(np.logaddexp.reduce(selected.ravel()))


def log_convolve(first, second, limit):
    if first.shape[1] > second.shape[1]:
        first, second = second, first
    first_length, first_parity = first.shape[1:]
    second_length, second_parity = second.shape[1:]
    length = min(limit + 1, first_length + second_length - 1)
    parity_size = max(first_parity, second_parity)
    if first_length == 1:
        if first_parity == 1 or second_parity == 1:
            return first + second[:, :length]
        return np.logaddexp(
            first[:, :, 0:1] + second[:, :length],
            first[:, :, 1:2] + second[:, :length, ::-1],
        )
    result = np.full((first.shape[0], length, parity_size), -np.inf)
    for offset in range(min(first_length, length)):
        available = min(second_length, length - offset)
        target = result[:, offset:offset + available]
        if first_parity == 1 or second_parity == 1:
            contribution = first[:, offset:offset + 1] + second[:, :available]
            np.logaddexp(target, contribution, out=target)
        else:
            contribution = first[:, offset:offset + 1, 0:1] + second[:, :available]
            np.logaddexp(target, contribution, out=target)
            contribution = first[:, offset:offset + 1, 1:2] + second[:, :available, ::-1]
            np.logaddexp(target, contribution, out=target)
    return result


def solve(data):
    model = EliminationModel(int(data["n"]), learn_interactions(data))
    normalizers = {}
    output = np.empty(len(data["log_activity"]), dtype=np.float64)
    for query, activity_value in enumerate(data["log_activity"]):
        activity = float(activity_value)
        if activity not in normalizers:
            normalizers[activity] = model.log_partition(activity)
        numerator = model.log_event_partition(
            activity, data["fixed"][query], data["count_mask"][query],
            data["weight_lo"][query], data["weight_hi"][query],
            data["parity_mask"][query], int(data["parity_value"][query]),
        )
        output[query] = min(0.0, numerator - normalizers[activity])
    return output


def main(input_path, output_path):
    with np.load(input_path, allow_pickle=False) as data:
        output = solve(data)
    with open(output_path, "wb") as output_file:
        np.savez(output_file, log_event=output)


if __name__ == "__main__":
    main(*sys.argv[1:])
