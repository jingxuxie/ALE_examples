import importlib.util
import math
import random
from collections import Counter
from pathlib import Path


def baseline_module():
    path = Path(__file__).resolve().parents[2] / 'participant/baseline/solve.py'
    spec = importlib.util.spec_from_file_location('portfolio_baseline', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def baseline_choices(graph, term_number):
    module = baseline_module()
    records = module.term_frontier(graph.case, graph.case['terms'][term_number])
    tree = min((record for record in records if record[1] <= graph.case['memory_cap']), key=lambda record: (record[0], record[1]))[2]
    choices = {}

    def visit(node):
        if isinstance(node, int):
            return 1 << node
        children, boundary = node
        left, right = visit(children[0]), visit(children[1])
        mask = left | right
        parent = graph.tables[term_number][mask][0]
        child_ids = sorted([graph.tables[term_number][left][0], graph.tables[term_number][right][0]])
        choices[parent] = next(edge_id for edge_id in graph.nodes[parent].edges if sorted(graph.edges[edge_id].children) == child_ids)
        return mask

    visit(tree)
    return choices


def root_order(graph, choices, mode, seed=0):
    rng = random.Random(seed)
    roots = list(range(len(graph.roots)))
    if mode == 'original':
        return roots
    if mode == 'random':
        rng.shuffle(roots)
        return roots
    active = [graph.reachable(choices, [root[0]]) for root in graph.roots]
    if mode == 'large':
        return sorted(roots, key=lambda index: (-graph.nodes[graph.roots[index][0]].size, -graph.minimum[graph.roots[index][0]]))
    if mode == 'small':
        return sorted(roots, key=lambda index: graph.nodes[graph.roots[index][0]].size)
    chosen = []
    retained = set()
    remaining = set(roots)
    while remaining:
        values = {}
        for index in remaining:
            missing = sum(graph.edges[choices[node_id]].cost for node_id in active[index] - retained)
            saved = sum(graph.edges[choices[node_id]].cost for node_id in active[index] & retained)
            future = sum(graph.edges[choices[node_id]].cost * len(graph.nodes[node_id].roots & remaining) for node_id in active[index])
            jitter = math.exp(rng.uniform(-0.6, 0.6)) if seed else 1
            values[index] = jitter * ((saved + 0.01 * future) / max(1, missing))
        index = max(remaining, key=lambda index: (values[index], -index))
        remaining.remove(index)
        chosen.append(index)
        retained |= active[index]
        future_nodes = set().union(*(active[pending] for pending in remaining)) if remaining else set()
        retained &= future_nodes
    return chosen


class Scheduler:
    def __init__(self, graph, choices, order, eviction='value', retention=True):
        self.graph = graph
        self.choices = choices
        self.order = order
        self.eviction = eviction
        self.retention = retention
        self.steps = []
        self.live = {}
        self.memory = 0
        self.counter = 0
        self.position = 0
        self.built = Counter()
        self.evictions = 0
        self.fallbacks = 0
        self.need = {}
        for position, term_number in enumerate(order):
            for node_id in graph.reachable(choices, [graph.roots[term_number][0]]):
                self.need.setdefault(node_id, []).append(position)

    def drop(self, node_id):
        self.steps.append({'delete': self.live.pop(node_id)})
        self.memory -= self.graph.nodes[node_id].size

    def eviction_value(self, node_id):
        pending = [position for position in self.need.get(node_id, []) if position >= self.position]
        if not pending:
            return (-1, 0)
        distance = pending[0] - self.position + 1
        size = self.graph.nodes[node_id].size
        value = self.graph.minimum[node_id]
        if self.eviction == 'belady':
            return (1 / distance, value / max(1, size))
        if self.eviction == 'size':
            return (1 / max(1, size), 1 / distance)
        if self.eviction == 'value':
            return (value / max(1, size) / distance, len(pending))
        return (value * len(pending) / max(1, size) / math.sqrt(distance), -size)

    def make_room(self, size, pinned):
        while self.memory + size > self.graph.case['memory_cap']:
            available = set(self.live) - pinned
            if not available:
                raise MemoryError('fixed DAG requires a different tree or evaluation order')
            victim = min(available, key=lambda node_id: (self.eviction_value(node_id), node_id))
            self.drop(victim)
            self.evictions += 1

    def peak(self, node_id, choices, memo):
        if node_id in memo:
            return memo[node_id]
        node = self.graph.nodes[node_id]
        if node.tensor or node_id in self.live:
            return 0, 0
        edge = self.graph.edges[choices[node_id]]
        left, right = edge.children
        first_peak, first_size = self.peak(left, choices, memo)
        second_peak, second_size = self.peak(right, choices, memo)
        allocation = first_size + second_size + node.size
        peak = min(max(first_peak, first_size + second_peak, allocation), max(second_peak, second_size + first_peak, allocation))
        memo[node_id] = (peak, node.size)
        return memo[node_id]

    def build(self, node_id, pinned, choices):
        node = self.graph.nodes[node_id]
        if node.tensor:
            return node.tensor
        if node_id in self.live:
            return self.live[node_id]
        edge = self.graph.edges[choices[node_id]]
        first, second = edge.children
        first_peak, first_size = self.peak(first, choices, {})
        second_peak, second_size = self.peak(second, choices, {})
        if max(first_peak, first_size + second_peak) > max(second_peak, second_size + first_peak):
            first, second = second, first
        self.build(first, pinned, choices)
        second_pinned = pinned | ({first} if not self.graph.nodes[first].tensor else set())
        self.build(second, second_pinned, choices)
        operands = {child for child in edge.children if not self.graph.nodes[child].tensor}
        self.make_room(node.size, pinned | operands)
        references = [[self.graph.nodes[child].tensor or self.live[child], axes] for child, axes in zip(edge.children, edge.inputs)]
        name = 'portfolio_' + str(self.counter)
        self.counter += 1
        self.steps.append({'id': name, 'inputs': references, 'output': edge.output})
        self.live[node_id] = name
        self.memory += node.size
        self.built[node_id] += 1
        for child in operands - pinned:
            future = any(position >= self.position for position in self.need.get(child, []))
            if not self.retention or not future:
                self.drop(child)
        return name

    def run(self):
        for position, term_number in enumerate(self.order):
            self.position = position
            snapshot = (len(self.steps), dict(self.live), self.memory, self.counter, self.built.copy(), self.evictions)
            root, axes, output = self.graph.roots[term_number]
            try:
                reference = self.build(root, set(), self.choices)
            except MemoryError:
                step_count, self.live, self.memory, self.counter, self.built, self.evictions = snapshot
                del self.steps[step_count:]
                for node_id in list(self.live):
                    self.drop(node_id)
                choices = dict(self.choices)
                choices.update(baseline_choices(self.graph, term_number))
                retention = self.retention
                self.retention = False
                reference = self.build(root, set(), choices)
                self.retention = retention
                self.fallbacks += 1
            self.steps.append({'emit': term_number, 'input': [reference, axes], 'output': output})
            for node_id in list(self.live):
                if not any(future > position for future in self.need.get(node_id, [])):
                    self.drop(node_id)
        return {'steps': self.steps}, {'evictions': self.evictions, 'fallbacks': self.fallbacks,
                                       'recomputed_nodes': sum(max(0, count - 1) for count in self.built.values())}
