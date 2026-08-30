import itertools
import math
from collections import defaultdict


def canonical(factors, boundary):
    groups = defaultdict(list)
    for name, axes in factors:
        groups[name].append(axes)
    names = sorted(groups)
    orders = [tuple(set(itertools.permutations(groups[name]))) for name in names]
    best = None
    best_axes = None
    for blocks in itertools.product(*orders):
        labels = {}
        opened = []
        encoded = []
        for name, block in zip(names, blocks):
            for axes in block:
                converted = []
                for axis in axes:
                    if axis not in labels:
                        labels[axis] = 2 * len(labels) + (axis not in boundary)
                        if axis in boundary:
                            opened.append(axis)
                    converted.append(labels[axis])
                encoded.append((name, tuple(converted)))
        key = tuple(encoded)
        if best is None or key < best:
            best = key
            best_axes = ''.join(opened)
    return best, best_axes


class Node:
    __slots__ = ('number', 'key', 'size', 'count', 'source', 'ops', 'opkeys',
                 'roots', 'rootmask', 'emits', 'base', 'minpeak', 'potential')

    def __init__(self, number, key, size, count, source):
        self.number = number
        self.key = key
        self.size = size
        self.count = count
        self.source = source
        self.ops = []
        self.opkeys = set()
        self.roots = set()
        self.rootmask = 0
        self.emits = []
        self.base = 0
        self.minpeak = 0
        self.potential = 1


class Graph:
    def __init__(self, case):
        self.case = case
        self.cap = case['memory_cap']
        self.nodes = []
        self.bykey = {}
        self.roots = []
        dimensions = case['dimensions']
        kinds = case['index_types']

        def volume(axes):
            return math.prod(dimensions[kinds[axis]] for axis in axes)

        for term_number, term in enumerate(case['terms']):
            factors = term['inputs']
            count = len(factors)
            complete = (1 << count) - 1
            factor_axes = [set(axes) for name, axes in factors]
            target_axes = set(term['output'])
            unions = [set() for mask in range(complete + 1)]
            for mask in range(1, complete + 1):
                bit = mask & -mask
                unions[mask] = unions[mask ^ bit] | factor_axes[bit.bit_length() - 1]
            boundaries = [None] * (complete + 1)
            ids = [None] * (complete + 1)
            axes_orders = [None] * (complete + 1)
            for mask in range(1, complete + 1):
                boundary = unions[mask] & (unions[complete ^ mask] | target_axes)
                if not mask & (mask - 1):
                    boundary = unions[mask]
                boundaries[mask] = boundary
                selected = [factors[position] for position in range(count) if mask >> position & 1]
                key, axes = canonical(selected, boundary)
                axes_orders[mask] = axes
                if key not in self.bykey:
                    number = len(self.nodes)
                    self.bykey[key] = number
                    source = selected[0][0] if len(selected) == 1 else None
                    self.nodes.append(Node(number, key, volume(boundary), len(selected), source))
                ids[mask] = self.bykey[key]
            root = ids[complete]
            if root not in self.roots:
                self.roots.append(root)
            self.nodes[root].emits.append((term_number, axes_orders[complete], term['output']))
            for mask in range(1, complete + 1):
                node = self.nodes[ids[mask]]
                node.roots.add(root)
                if node.source is not None:
                    continue
                left = (mask - 1) & mask
                while left:
                    right = mask ^ left
                    if left < right:
                        first = ids[left]
                        second = ids[right]
                        merged = boundaries[left] | boundaries[right]
                        work = volume(merged) * (2 if merged - boundaries[mask] else 1)
                        opkey = (min(first, second), max(first, second), work)
                        if opkey not in node.opkeys:
                            node.opkeys.add(opkey)
                            node.ops.append((first, second, axes_orders[left], axes_orders[right], axes_orders[mask], work))
                    left = (left - 1) & mask
        self.order = sorted(range(len(self.nodes)), key=lambda number: self.nodes[number].count)
        self.rootbits = {root: 1 << position for position, root in enumerate(self.roots)}
        for number in self.order:
            node = self.nodes[number]
            node.potential = len(node.roots)
            node.rootmask = sum(self.rootbits[root] for root in node.roots)
            if node.source is None:
                node.base = min(sum(self.nodes[child].base for child in set(op[:2])) + op[5] for op in node.ops)
                node.minpeak = min(self._oppeak(node, op) for op in node.ops)

    def _oppeak(self, node, op):
        first = self.nodes[op[0]]
        second = self.nodes[op[1]]
        first_size = first.size if first.source is None else 0
        second_size = second.size if second.source is None else 0
        if op[0] == op[1]:
            return max(first.minpeak, first_size + node.size)
        allocation = first_size + second_size + node.size
        return min(max(first.minpeak, first_size + second.minpeak, allocation),
                   max(second.minpeak, second_size + first.minpeak, allocation))


def frontier(records):
    records.sort(key=lambda record: (record[0], record[1]))
    result = []
    peak = math.inf
    for record in records:
        if record[1] < peak:
            result.append(record)
            peak = record[1]
    return result


def dynamic_program(graph, cached, budget, weights, wanted=None, preferred=None, active=None, owned_cached=False):
    table = [None] * len(graph.nodes)
    sizes = [node.size if node.source is None and (owned_cached or node.number not in cached) else 0 for node in graph.nodes]
    for number in graph.order:
        node = graph.nodes[number]
        if wanted is not None and number not in wanted:
            continue
        if active is not None and not node.rootmask & active:
            continue
        if number in cached or node.source is not None:
            table[number] = [(0, sizes[number], number, None, None, None, False, 0)]
            continue
        if node.size > budget:
            table[number] = []
            continue
        choices = []
        operations = [preferred[number]] if preferred is not None and preferred[number] is not None else node.ops
        for op in operations:
            first, second = op[:2]
            if not table[first] or not table[second]:
                continue
            first_size = sizes[first]
            second_size = sizes[second]
            work = op[5] if weights[number] == 1 else op[5] * weights[number]
            if first == second:
                allocation = first_size + node.size
                for left in table[first]:
                    peak = max(left[1], allocation)
                    if peak <= budget:
                        choices.append((left[0] + work, peak, number, op, left, left, False, left[7] + op[5]))
                continue
            allocation = first_size + second_size + node.size
            if allocation > budget:
                continue
            for left in table[first]:
                for right in table[second]:
                    peak_left = max(left[1], first_size + right[1], allocation)
                    peak_right = max(right[1], second_size + left[1], allocation)
                    peak = min(peak_left, peak_right)
                    if peak <= budget:
                        choices.append((left[0] + right[0] + work, peak, number, op, left, right,
                                        peak_right < peak_left, left[7] + right[7] + op[5]))
        table[number] = frontier(choices)
    return table
