import itertools
import json
import math
import random
import sys
import time
from collections import defaultdict


class Node:
    __slots__ = ('number', 'count', 'axes', 'size', 'source', 'options', 'frequency', 'cost')

    def __init__(self, number, factors, axes, size):
        self.number = number
        self.count = len(factors)
        self.axes = axes
        self.size = size if len(factors) > 1 else 0
        self.source = factors[0][0] if len(factors) == 1 else None
        self.options = []
        self.frequency = 0
        self.cost = 0


class Tree:
    __slots__ = ('node', 'option', 'left', 'right', 'reverse', 'cost', 'peak', 'score')

    def __init__(self, node, option=None, left=None, right=None, reverse=False,
                 cost=0, peak=0, score=0):
        self.node = node
        self.option = option
        self.left = left
        self.right = right
        self.reverse = reverse
        self.cost = cost
        self.peak = peak
        self.score = score


def canonical(factors, boundary):
    occurrences = defaultdict(list)
    for position, (name, axes) in enumerate(factors):
        for axis in axes:
            occurrences[axis].append(position)
    neighbors = []
    for position, (name, axes) in enumerate(factors):
        neighbors.append([other for axis in axes for other in occurrences[axis] if other != position])
    pending = set(range(len(factors)))
    components = []
    while pending:
        first = min(pending)
        component = [first]
        discovered = {first}
        for position in component:
            for neighbor in neighbors[position]:
                if neighbor not in discovered:
                    discovered.add(neighbor)
                    component.append(neighbor)
        pending.difference_update(discovered)
        first_name = min(factors[position][0] for position in component)
        best = None
        best_axes = None
        for start in component:
            if factors[start][0] != first_name:
                continue
            ordering = [start]
            discovered = {start}
            for position in ordering:
                for neighbor in neighbors[position]:
                    if neighbor not in discovered:
                        discovered.add(neighbor)
                        ordering.append(neighbor)
            labels = {}
            encoded = []
            output = []
            for position in ordering:
                name, axes = factors[position]
                converted = []
                for axis in axes:
                    if axis not in labels:
                        labels[axis] = len(labels)
                        if axis in boundary:
                            output.append(axis)
                    converted.append(2 * labels[axis] + (axis in boundary))
                encoded.append((name, tuple(converted)))
            key = tuple(encoded)
            if best is None or key < best:
                best = key
                best_axes = ''.join(output)
        components.append((best, best_axes))
    components.sort(key=lambda item: item[0])
    return tuple(key for key, axes in components), ''.join(axes for key, axes in components)


class Graph:
    def __init__(self, case):
        self.case = case
        self.cap = case['memory_cap']
        self.nodes = []
        self.roots = {}
        self.targets = defaultdict(list)
        self.lookup = {}
        self.root_subsets = {}
        self.intra_reuse = False
        sizes = {axis: case['dimensions'][kind] for axis, kind in case['index_types'].items()}

        def volume(axes):
            return math.prod(sizes[axis] for axis in set(axes))

        for term_number, term in enumerate(case['terms']):
            factors = term['inputs']
            complete = (1 << len(factors)) - 1
            full_key, full_axes = canonical(factors, set(term['output']))
            previous = self.lookup.get(full_key)
            if previous in self.roots:
                self.targets[previous].append((term_number, full_axes, term['output']))
                continue
            table = {}
            fresh = []
            for mask in range(1, complete + 1):
                selected = tuple((name, axes) for position, (name, axes) in enumerate(factors)
                                 if mask & (1 << position))
                inside = set().union(*(set(axes) for name, axes in selected))
                outside = set(term['output'])
                for position, (name, axes) in enumerate(factors):
                    if not mask & (1 << position):
                        outside.update(axes)
                boundary = inside & outside if len(selected) > 1 else inside
                if mask == complete:
                    key, axes = full_key, full_axes
                else:
                    key, axes = canonical(selected, boundary)
                node_number = self.lookup.get(key)
                if node_number is None:
                    node_number = len(self.nodes)
                    self.lookup[key] = node_number
                    self.nodes.append(Node(node_number, selected, axes, volume(axes)))
                    fresh.append(mask)
                table[mask] = (node_number, axes)
            for mask in fresh:
                node_number, axes = table[mask]
                node = self.nodes[node_number]
                if node.count == 1:
                    continue
                left_mask = (mask - 1) & mask
                seen = set()
                while left_mask:
                    right_mask = mask ^ left_mask
                    if left_mask < right_mask:
                        left, left_axes = table[left_mask]
                        right, right_axes = table[right_mask]
                        input_axes = set(left_axes) | set(right_axes)
                        work = volume(input_axes) * (2 if input_axes - set(axes) else 1)
                        allocation = self.nodes[left].size + self.nodes[right].size + node.size
                        if left == right:
                            allocation -= self.nodes[right].size
                        pair = (min(left, right), max(left, right), work)
                        if allocation <= self.cap and pair not in seen:
                            node.options.append((left, right, work, left_axes, right_axes))
                            seen.add(pair)
                    left_mask = (left_mask - 1) & mask
            root, axes = table[complete]
            internal = [number for number, axes in table.values() if self.nodes[number].source is None]
            if len(internal) != len(set(internal)):
                self.intra_reuse = True
            self.roots[root] = root
            self.targets[root].append((term_number, axes, term['output']))
            self.root_subsets[root] = {node for node, axes in table.values()}
        self.order = sorted(range(len(self.nodes)), key=lambda number: self.nodes[number].count)
        self.consumers = defaultdict(list)
        for root, subset in self.root_subsets.items():
            for number in subset:
                self.nodes[number].frequency += 1
                self.consumers[number].append(root)

    def plan_trees(self, alpha=0, frequencies=None, fixed=None, all_trees=False, return_table=False,
                   roots=None):
        frontiers = [None] * len(self.nodes)
        requested = self.roots if roots is None else roots
        if roots is None:
            order = self.order
        else:
            needed = set().union(*(self.root_subsets[root] for root in requested))
            order = sorted(needed, key=lambda number: self.nodes[number].count)
        for number in order:
            node = self.nodes[number]
            if node.source is not None:
                frontiers[number] = [Tree(number)]
                continue
            frequency = node.frequency if frequencies is None else frequencies.get(number, 1)
            weight = max(1, frequency) ** (-alpha) if alpha else 1
            if fixed and number in fixed:
                original = fixed[number]
                frontiers[number] = [Tree(number, original.option, original.left, original.right,
                                          original.reverse, original.cost, original.peak, 0)]
                continue
            records = []
            for option in node.options:
                left_number, right_number, work = option[:3]
                left_size = self.nodes[left_number].size
                right_size = self.nodes[right_number].size
                if left_number == right_number:
                    for child in frontiers[left_number]:
                        peak = max(child.peak, left_size + node.size)
                        if peak <= self.cap:
                            records.append(Tree(number, option, child, child, False,
                                                child.cost + work, peak, child.score + weight * work))
                    continue
                allocation = left_size + right_size + node.size
                for left, right in itertools.product(frontiers[left_number], frontiers[right_number]):
                    peak_left = max(left.peak, left_size + right.peak, allocation)
                    peak_right = max(right.peak, right_size + left.peak, allocation)
                    peak = min(peak_left, peak_right)
                    if peak <= self.cap:
                        records.append(Tree(number, option, left, right, peak_right < peak_left,
                                            left.cost + right.cost + work, peak,
                                            left.score + right.score + weight * work))
            records.sort(key=lambda tree: (tree.score, tree.peak))
            if all_trees:
                frontier = records
            else:
                frontier = []
                peak = self.cap + 1
                for tree in records:
                    if tree.peak < peak:
                        frontier.append(tree)
                        peak = tree.peak
            frontiers[number] = frontier
            if frontier and alpha == 0 and not fixed:
                node.cost = frontier[0].cost
        result = {}
        for root in requested:
            if not frontiers[root]:
                raise ValueError('No feasible contraction tree')
            result[root] = frontiers[root][0]
        return (result, frontiers) if return_table else result


def tree_nodes(tree, output=None):
    if output is None:
        output = {}
    if tree.option is not None and tree.node not in output:
        output[tree.node] = tree
        tree_nodes(tree.left, output)
        tree_nodes(tree.right, output)
    return output


def tree_signature(tree):
    if tree.option is None:
        return tree.node
    return (tree.node, tree.option[:3], tree.reverse,
            tree_signature(tree.left), tree_signature(tree.right))


def marginal_cost(tree, available):
    visited = set()

    def visit(current):
        if current.option is None or current.node in visited or current.node in available:
            return 0
        visited.add(current.node)
        first, second = (current.right, current.left) if current.reverse else (current.left, current.right)
        return current.option[2] + visit(first) + visit(second)

    return visit(tree)


def simulate(graph, trees, policy=0, eviction=1.0, order=None):
    root_nodes = {root: tree_nodes(tree) for root, tree in trees.items()}
    future = defaultdict(int)

    def count_queries(tree, increment):
        if tree.option is not None:
            future[tree.node] += increment
            count_queries(tree.left, increment)
            count_queries(tree.right, increment)

    for tree in trees.values():
        count_queries(tree, 1)
    remaining = set(trees)
    live = {}
    pins = defaultdict(int)
    steps = []
    memory = 0
    peak = 0
    work = 0
    serial = 0
    nodes = graph.nodes
    cap = graph.cap
    names = set(graph.case['tensors'])
    schedule = []
    current_root = None
    materialized = set()
    recomputation = 0

    def drop(number):
        nonlocal memory
        steps.append({'delete': live.pop(number)})
        memory -= nodes[number].size

    def emit(number):
        if number not in remaining:
            return
        for term_number, axes, output in graph.targets[number]:
            steps.append({'emit': term_number, 'input': [live[number], axes], 'output': output})
        remaining.remove(number)
        if number != current_root:
            count_queries(trees[number], -1)

    def evaluate(tree):
        nonlocal memory, peak, work, serial, recomputation
        number = tree.node
        node = nodes[number]
        if node.source is not None:
            return node.source
        future[number] -= 1
        if number in live:
            count_queries(tree.left, -1)
            count_queries(tree.right, -1)
            pins[number] += 1
            return live[number]
        if tree.reverse:
            right_name = evaluate(tree.right)
            left_name = evaluate(tree.left)
        else:
            left_name = evaluate(tree.left)
            right_name = evaluate(tree.right)
        for unused in list(live):
            if not pins[unused] and not future[unused]:
                drop(unused)
        while memory + node.size > cap:
            candidates = [candidate for candidate in live if not pins[candidate]]
            if not candidates:
                raise ValueError('Infeasible live tree')
            victim = min(candidates, key=lambda candidate: (
                future[candidate] > 0,
                nodes[candidate].cost * max(1, future[candidate]) / nodes[candidate].size ** eviction,
                -nodes[candidate].size))
            drop(victim)
        while True:
            name = 'intermediate_' + str(serial)
            serial += 1
            if name not in names:
                break
        names.add(name)
        option = tree.option
        steps.append({'id': name, 'inputs': [[left_name, option[3]], [right_name, option[4]]],
                      'output': node.axes})
        live[number] = name
        pins[number] += 1
        memory += node.size
        peak = max(peak, memory)
        work += option[2]
        if number in materialized:
            recomputation += option[2]
        materialized.add(number)
        emit(number)
        for child in (tree.left, tree.right):
            if nodes[child.node].source is None:
                pins[child.node] -= 1
                if not pins[child.node] and not future[child.node] and child.node in live:
                    drop(child.node)
        return name

    def marginal(tree, visited):
        if tree.node in live or tree.node in visited or tree.option is None:
            return 0
        visited.add(tree.node)
        return tree.option[2] + marginal(tree.left, visited) + marginal(tree.right, visited)

    while remaining:
        if order is not None:
            root = next(root for root in order if root in remaining)
        elif policy == 2:
            root = max(remaining, key=lambda root: (trees[root].cost, -root))
        elif policy == 3:
            root = min(remaining, key=lambda root: (trees[root].cost, root))
        else:
            def priority(root):
                cost = max(1, trees[root].cost)
                saved = 1 - marginal(trees[root], set()) / cost
                benefit = sum(nodes[number].cost * (future[number] - 1)
                              for number in root_nodes[root] if future[number] > 1)
                if policy == 0:
                    return (saved + 0.12 * benefit / cost, benefit, -cost, -root)
                return (saved, benefit / cost, -cost, -root)
            root = max(remaining, key=priority)
        current_root = root
        schedule.append(root)
        evaluate(trees[root])
        pins[root] -= 1
        for number in list(live):
            if not pins[number] and not future[number]:
                drop(number)
    for number in list(live):
        drop(number)
    return work, peak, {'steps': steps}, schedule, recomputation


def solve(case):
    started = time.monotonic()
    deadline = started + 20
    graph = Graph(case)
    best = None
    best_trees = None
    best_policy = 0
    best_eviction = 1.0
    tested = set()

    def attempt(trees, thorough=False):
        nonlocal best, best_trees, best_policy, best_eviction
        signature = tuple(hash(tree_signature(tree)) for tree in trees.values())
        settings = [(best_policy, best_eviction), (0, 1.0), (1, 0.65), (2, 1.0)]
        if thorough:
            settings = [(policy, eviction) for policy in range(4) for eviction in (0.65, 1.0)]
        improved = False
        for policy, eviction in settings:
            if best is not None and time.monotonic() > deadline:
                break
            key = (signature, policy, eviction)
            if key in tested:
                continue
            tested.add(key)
            candidate = simulate(graph, trees, policy, eviction)
            if best is None or candidate[:2] < best[:2]:
                best = candidate
                best_trees = trees
                best_policy = policy
                best_eviction = eviction
                improved = True
        return improved

    inter_reuse = any(node.frequency > 1 and node.source is None for node in graph.nodes)
    alphas = (0, 0.5, 0.85, 1.0, 1.3, 2.0) if inter_reuse else (0,)
    for alpha in alphas:
        if best is not None and time.monotonic() > deadline:
            return best[2]
        trees = graph.plan_trees(alpha)
        attempt(trees, thorough=True)
    if not graph.intra_reuse and not inter_reuse:
        return best[2]
    if time.monotonic() > deadline:
        return best[2]
    _, alternatives = graph.plan_trees(all_trees=True, return_table=True)
    if time.monotonic() > deadline:
        return best[2]
    own_cost = {}
    for root in graph.roots:
        for tree in alternatives[root]:
            own_cost[id(tree)] = marginal_cost(tree, set())
    trees = {root: min(alternatives[root], key=lambda tree: (own_cost[id(tree)], tree.peak))
             for root in graph.roots}
    attempt(trees, thorough=True)
    generator = random.Random(7319)
    for iteration in range(4):
        improved = False
        roots = list(graph.roots)
        if iteration == 0:
            roots.sort(key=lambda root: -best_trees[root].cost)
        else:
            generator.shuffle(roots)
        for root in roots:
            if time.monotonic() > deadline:
                return best[2]
            fixed = {}
            for other, tree in best_trees.items():
                if other != root:
                    tree_nodes(tree, fixed)
            replacements = sorted(alternatives[root], key=lambda tree: (
                marginal_cost(tree, fixed), own_cost[id(tree)], tree.peak))[:4]
            replacements.append(graph.plan_trees(0, fixed=fixed, roots=(root,))[root])
            for replacement in replacements:
                trees = dict(best_trees)
                trees[root] = replacement
                improved |= attempt(trees)
        if iteration < 2:
            counts = defaultdict(int)
            active = {}
            for tree in best_trees.values():
                subset = tree_nodes(tree)
                for number in subset:
                    counts[number] += 1
                active.update(subset)
            candidates = [node.number for node in graph.nodes if node.source is None
                          and node.frequency > 1 and alternatives[node.number]]
            candidates.sort(key=lambda number: (
                -graph.nodes[number].cost * max(1, graph.nodes[number].frequency - counts[number]),
                graph.nodes[number].size))
            for number in candidates:
                if time.monotonic() > deadline:
                    return best[2]
                promoted = alternatives[number][0]
                fixed = {number: promoted}
                affected = graph.consumers[number]
                trees = dict(best_trees)
                trees.update(graph.plan_trees(0, fixed=fixed, roots=affected))
                improved |= attempt(trees)
                fixed.update((node, tree) for node, tree in active.items()
                             if counts[node] > 1 and node != number)
                trees = dict(best_trees)
                trees.update(graph.plan_trees(0, fixed=fixed, roots=affected))
                improved |= attempt(trees)
        if not improved:
            break
    attempt(best_trees, thorough=True)
    if time.monotonic() < deadline:
        shared = defaultdict(list)
        for root, tree in best_trees.items():
            for number in tree_nodes(tree):
                shared[number].append(root)
        groups = [consumers for consumers in shared.values() if len(consumers) > 1]
        order = best[3] + [root for root in graph.roots if root not in best[3]]
        trials = 240 if best[4] else 12
        tested_orders = set()
        for trial in range(trials):
            if time.monotonic() > deadline:
                break
            if trial % 20 == 0:
                order = best[3] + [root for root in graph.roots if root not in best[3]]
            candidate_order = list(order)
            if groups and trial % 3 == 0:
                group = set(generator.choice(groups))
                consumers = [root for root in candidate_order if root in group]
                others = [root for root in candidate_order if root not in group]
                position = generator.randrange(len(others) + 1)
                candidate_order = others[:position] + consumers + others[position:]
            elif len(order) > 1:
                first, second = generator.sample(range(len(order)), 2)
                if trial % 2:
                    candidate_order[first], candidate_order[second] = candidate_order[second], candidate_order[first]
                else:
                    candidate_order.insert(second, candidate_order.pop(first))
            eviction = (best_eviction, 0.0, 1.0, 1.5)[trial % 4]
            key = (tuple(candidate_order), eviction)
            if key in tested_orders:
                continue
            tested_orders.add(key)
            candidate = simulate(graph, best_trees, eviction=eviction, order=candidate_order)
            if candidate[:2] <= best[:2]:
                order = candidate_order
                if candidate[:2] < best[:2]:
                    best = candidate
                    best_eviction = eviction
    return best[2]


def main():
    with open(sys.argv[1]) as source:
        case = json.load(source)
    plan = solve(case)
    with open(sys.argv[2], 'w') as destination:
        json.dump(plan, destination, separators=(',', ':'))


if __name__ == '__main__':
    main()
