import itertools
import math
from collections import defaultdict
from dataclasses import dataclass, field


@dataclass
class Edge:
    parent: int
    children: tuple
    inputs: tuple
    output: str
    cost: int


@dataclass
class Node:
    key: tuple
    size: int
    rank: int
    order: int
    tensor: str = None
    edges: list = field(default_factory=list)
    roots: set = field(default_factory=set)


def normalize(factors, boundary):
    groups = defaultdict(list)
    for name, axes in factors:
        groups[name].append(axes)
    names = sorted(groups)
    options = [set(itertools.permutations(groups[name])) for name in names]
    best = None
    best_axes = None
    boundary = set(boundary)
    for ordering in itertools.product(*options):
        external = {}
        internal = {}
        encoded = []
        for name, block in zip(names, ordering):
            for axes in block:
                labels = []
                for axis in axes:
                    if axis in boundary:
                        if axis not in external:
                            external[axis] = len(external)
                        labels.append(external[axis])
                    else:
                        if axis not in internal:
                            internal[axis] = len(boundary) + len(internal)
                        labels.append(internal[axis])
                encoded.append((name, tuple(labels)))
        key = (len(boundary), tuple(encoded))
        if best is None or key < best:
            best = key
            best_axes = ''.join(external)
    return best, best_axes


class Graph:
    def __init__(self, case, delayed=False):
        self.case = case
        self.nodes = []
        self.edges = []
        self.roots = []
        self.lookup = {}
        self.term_nodes = []
        self.tables = []
        if delayed:
            self.build_delayed()
            self.finish()
            return
        seen_edges = set()
        for term_number, term in enumerate(case['terms']):
            inputs = term['inputs']
            count = len(inputs)
            complete = (1 << count) - 1
            table = {}
            for mask in range(1, complete + 1):
                factors = [inputs[position] for position in range(count) if mask >> position & 1]
                inside = set().union(*(set(axes) for name, axes in factors))
                outside = set(term['output']).union(*(set(inputs[position][1]) for position in range(count) if not mask >> position & 1))
                boundary = inside & outside
                key, axes = normalize(factors, boundary)
                if key not in self.lookup:
                    node_id = len(self.nodes)
                    self.lookup[key] = node_id
                    tensor = factors[0][0] if len(factors) == 1 else None
                    self.nodes.append(Node(key, 0 if tensor else self.volume(axes), len(axes), len(factors), tensor))
                node_id = self.lookup[key]
                self.nodes[node_id].roots.add(term_number)
                table[mask] = (node_id, axes)
                if len(factors) == 1:
                    continue
                left = (mask - 1) & mask
                while left:
                    right = mask ^ left
                    if left < right:
                        first, first_axes = table[left]
                        second, second_axes = table[right]
                        union = set(first_axes) | set(second_axes)
                        cost = self.volume(union) * (2 if union - boundary else 1)
                        signature = (node_id, min(first, second), max(first, second), cost)
                        if signature not in seen_edges:
                            seen_edges.add(signature)
                            edge_id = len(self.edges)
                            self.edges.append(Edge(node_id, (first, second), (first_axes, second_axes), axes, cost))
                            self.nodes[node_id].edges.append(edge_id)
                    left = (left - 1) & mask
            self.roots.append((table[complete][0], table[complete][1], term['output']))
            self.term_nodes.append({value[0] for value in table.values()})
            self.tables.append(table)
        self.finish()

    def finish(self):
        self.topological = sorted(range(len(self.nodes)), key=lambda node_id: self.nodes[node_id].order)
        self.minimum = [0] * len(self.nodes)
        self.base_choices = {}
        for node_id in self.topological:
            node = self.nodes[node_id]
            if node.tensor:
                continue
            if not node.edges:
                self.minimum[node_id] = math.inf
                continue
            edge_id = min(node.edges, key=lambda edge_id: self.edges[edge_id].cost + sum(self.minimum[child] for child in self.edges[edge_id].children))
            self.base_choices[node_id] = edge_id
            self.minimum[node_id] = self.edges[edge_id].cost + sum(self.minimum[child] for child in self.edges[edge_id].children)

    def build_delayed(self):
        seen_edges = set()
        for term_number, term in enumerate(self.case['terms']):
            inputs = term['inputs']
            count = len(inputs)
            complete = (1 << count) - 1
            states = {}
            ordinary = {}
            term_nodes = set()
            for mask in range(1, complete + 1):
                factors = [inputs[position] for position in range(count) if mask >> position & 1]
                inside = set().union(*(set(axes) for name, axes in factors))
                outside = set(term['output']).union(*(set(inputs[position][1]) for position in range(count) if not mask >> position & 1))
                mandatory = inside & outside
                optional = sorted(inside - mandatory)
                variants = {}
                for retained in range(1 << len(optional)):
                    boundary = mandatory | {axis for position, axis in enumerate(optional) if retained >> position & 1}
                    if len(factors) > 1 and self.volume(boundary) > self.case['memory_cap']:
                        continue
                    key, axes = normalize(factors, boundary)
                    if key not in self.lookup:
                        node_id = len(self.nodes)
                        self.lookup[key] = node_id
                        tensor = factors[0][0] if len(factors) == 1 else None
                        self.nodes.append(Node(key, 0 if tensor else self.volume(axes), len(axes), len(factors), tensor))
                    node_id = self.lookup[key]
                    self.nodes[node_id].roots.add(term_number)
                    variants[frozenset(boundary)] = (node_id, axes)
                    term_nodes.add(node_id)
                    if retained == 0:
                        ordinary[mask] = (node_id, axes)
                states[mask] = variants
                if len(factors) == 1:
                    continue
                left = (mask - 1) & mask
                while left:
                    right = mask ^ left
                    if left < right:
                        for (first_boundary, (first, first_axes)), (second_boundary, (second, second_axes)) in itertools.product(states[left].items(), states[right].items()):
                            if (not self.nodes[first].tensor and not self.nodes[first].edges) or (not self.nodes[second].tensor and not self.nodes[second].edges):
                                continue
                            union = first_boundary | second_boundary
                            for boundary, (node_id, axes) in variants.items():
                                if not boundary <= union:
                                    continue
                                allocation = self.nodes[node_id].size + sum(self.nodes[child].size for child in {first, second})
                                if allocation > self.case['memory_cap']:
                                    continue
                                cost = self.volume(union) * (2 if union - boundary else 1)
                                signature = (node_id, min(first, second), max(first, second), cost)
                                if signature in seen_edges:
                                    continue
                                seen_edges.add(signature)
                                edge_id = len(self.edges)
                                self.edges.append(Edge(node_id, (first, second), (first_axes, second_axes), axes, cost))
                                self.nodes[node_id].edges.append(edge_id)
                    left = (left - 1) & mask
            self.roots.append((ordinary[complete][0], ordinary[complete][1], term['output']))
            self.term_nodes.append(term_nodes)
            self.tables.append(ordinary)

    def volume(self, axes):
        return math.prod(self.case['dimensions'][self.case['index_types'][axis]] for axis in set(axes))

    def reachable(self, choices, roots=None):
        active = set()
        stack = [root[0] for root in self.roots] if roots is None else list(roots)
        while stack:
            node_id = stack.pop()
            if node_id in active or self.nodes[node_id].tensor:
                continue
            active.add(node_id)
            stack.extend(self.edges[choices[node_id]].children)
        return active

    def cost(self, choices, roots=None):
        return sum(self.edges[choices[node_id]].cost for node_id in self.reachable(choices, roots))

    def statistics(self):
        return {'nodes': len(self.nodes), 'edges': len(self.edges),
                'roots': len(self.roots), 'unique_roots': len({root[0] for root in self.roots}),
                'shared_nodes': sum(len(node.roots) > 1 and not node.tensor for node in self.nodes),
                'independent_minimum': sum(self.minimum[root[0]] for root in self.roots),
                'baseline_tree_union': self.cost(self.base_choices)}
