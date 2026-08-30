import copy
import json
import math
import random
import sys
import time

from model import Graph, dynamic_program


class Planner:
    def __init__(self, graph, exponent=0.0, ordering=0, preferred=None, retain=True, release=False,
                 frequency_power=0.5, size_power=0.7, marginal=False, lookahead=0, seed=0):
        self.graph = graph
        self.nodes = graph.nodes
        self.exponent = exponent
        self.ordering = ordering
        self.preferred = preferred
        self.retain = retain
        self.release = release
        self.cache_uses = None
        self.frequency_power = frequency_power
        self.size_power = size_power
        self.marginal = marginal
        self.lookahead = lookahead
        self.seed = seed
        generator = random.Random(seed)
        self.noise = [generator.random() for node in self.nodes]
        self.recompute = None
        self.users = [node.roots for node in self.nodes]
        if preferred is not None:
            self.users = [set() for node in self.nodes]
            for root in graph.roots:
                pending = [root]
                visited = set()
                while pending:
                    number = pending.pop()
                    if number in visited:
                        continue
                    visited.add(number)
                    self.users[number].add(root)
                    if preferred[number] is not None:
                        pending.extend(preferred[number][:2])
        self.steps = []
        self.live = {}
        self.memory = 0
        self.peak = 0
        self.work = 0
        self.counter = 0
        self.remaining = set(graph.roots)
        self.remaining_mask = (1 << len(graph.roots)) - 1
        self.user_masks = [sum(graph.rootbits[root] for root in users) for users in self.users]
        self.emitted = set()
        self.protected = set()
        self.pinned = {}
        self.lastused = {}
        self.clock = 0
        self.weights = [1.0 / max(1, node.potential) ** exponent for node in self.nodes]

    def delete(self, number):
        name = self.live.pop(number)
        self.memory -= self.nodes[number].size
        self.steps.append({'delete': name})
        self.recompute = None

    def value(self, number):
        node = self.nodes[number]
        future = (self.user_masks[number] & self.remaining_mask).bit_count()
        if not future:
            return -1
        cost = node.base if self.recompute is None else self.recompute.get(number, node.base)
        return cost * (future ** self.frequency_power) / max(1, node.size) ** self.size_power

    def victim(self, choices=None):
        choices = list(self.live) if choices is None else choices
        self.recompute = None
        if self.marginal:
            costs = {number: 0 for number in self.live}

            def cost(number):
                if number not in costs:
                    node = self.nodes[number]
                    if node.source is not None:
                        costs[number] = 0
                    else:
                        costs[number] = min(op[5] + sum(cost(child) for child in set(op[:2])) for op in node.ops)
                return costs[number]

            self.recompute = {number: min(op[5] + sum(cost(child) for child in set(op[:2]))
                                         for op in self.nodes[number].ops) for number in choices}
        return min(choices, key=lambda number: (self.value(number), self.lastused.get(number, 0)))

    def evict(self, required=0):
        while self.memory + required > self.graph.cap:
            choices = [number for number in self.live if number not in self.protected and not self.pinned.get(number)]
            if not choices:
                raise RuntimeError('cannot allocate')
            victim = self.victim(choices)
            self.delete(victim)

    def emit(self, number):
        if number in self.remaining:
            for term_number, axes, output in self.nodes[number].emits:
                self.steps.append({'emit': term_number, 'input': [self.live[number], axes], 'output': output})
                self.emitted.add(term_number)
            self.remaining.remove(number)
            self.remaining_mask &= ~self.graph.rootbits[number]

    def consume_cached(self, number):
        if self.cache_uses is not None and number in self.cache_uses:
            self.cache_uses[number] -= 1
            if self.cache_uses[number] == 0:
                self.protected.discard(number)

    def skip_cached_reads(self, record):
        if self.cache_uses is None:
            return
        pending = [record]
        while pending:
            current = pending.pop()
            if current[3] is not None:
                for child in (current[4], current[5]):
                    if child[2] in self.cache_uses:
                        self.consume_cached(child[2])
                    else:
                        pending.append(child)

    def execute(self, record):
        number = record[2]
        node = self.nodes[number]
        self.clock += 1
        self.lastused[number] = self.clock
        if node.source is not None:
            return node.source
        if number in self.live:
            self.skip_cached_reads(record)
            self.emit(number)
            return self.live[number]
        op = record[3]
        if op is None:
            raise RuntimeError('evicted planned cache')
        first, second = op[:2]
        children = (record[5], record[4]) if record[6] else (record[4], record[5])
        for child in children:
            self.execute(child)
            child_number = child[2]
            self.pinned[child_number] = self.pinned.get(child_number, 0) + 1
        self.evict(node.size)
        name = '_p' + str(self.counter)
        self.counter += 1
        while name in self.graph.case['tensors']:
            name = '_p' + str(self.counter)
            self.counter += 1
        first_source = self.nodes[first].source
        second_source = self.nodes[second].source
        first_name = first_source if first_source is not None else self.live[first]
        second_name = second_source if second_source is not None else self.live[second]
        self.steps.append({'id': name, 'inputs': [[first_name, op[2]], [second_name, op[3]]], 'output': op[4]})
        self.live[number] = name
        self.memory += node.size
        self.peak = max(self.peak, self.memory)
        self.work += op[5]
        self.emit(number)
        for child in children:
            child_number = child[2]
            self.pinned[child_number] -= 1
            self.consume_cached(child_number)
            if child_number in self.live and child_number not in self.protected and not self.pinned[child_number]:
                if not self.retain or not (self.user_masks[child_number] & self.remaining_mask):
                    self.delete(child_number)
        return name

    def trial(self, record):
        planner = copy.copy(self)
        planner.steps = self.steps.copy()
        planner.live = self.live.copy()
        planner.remaining = self.remaining.copy()
        planner.emitted = self.emitted.copy()
        planner.pinned = self.pinned.copy()
        planner.lastused = self.lastused.copy()
        planner.cache_uses = {}
        pending = [record]
        while pending:
            current = pending.pop()
            if current[3] is not None:
                for child in (current[4], current[5]):
                    if child[2] in self.live:
                        planner.cache_uses[child[2]] = planner.cache_uses.get(child[2], 0) + 1
                    else:
                        pending.append(child)
        planner.protected = set(planner.cache_uses)
        try:
            planner.execute(record)
        except RuntimeError:
            return None
        planner.protected = set()
        planner.cache_uses = None
        return planner

    def solve(self, deadline=None):
        baseline = dynamic_program(self.graph, set(), self.graph.cap, [1.0] * len(self.nodes))
        root_costs = {root: baseline[root][0][0] for root in self.remaining}
        if self.preferred is not None:
            cold = dynamic_program(self.graph, set(), self.graph.cap, [1.0] * len(self.nodes),
                                   preferred=self.preferred)
            for root in self.remaining:
                if cold[root]:
                    root_costs[root] = cold[root][0][7]
        while self.remaining:
            if deadline is not None and time.monotonic() > deadline:
                return None
            for number in list(self.live):
                if not (self.user_masks[number] & self.remaining_mask):
                    self.delete(number)
            while True:
                cached = set(self.live)
                weights = [1.0 / max(1, (mask & self.remaining_mask).bit_count()) ** self.exponent for mask in self.user_masks]
                budget = self.graph.cap if self.release else self.graph.cap - self.memory
                table = dynamic_program(self.graph, cached, budget, weights,
                                        preferred=self.preferred, active=self.remaining_mask, owned_cached=self.release)
                candidates = [root for root in self.remaining if table[root]]
                if self.exponent == 0 and self.live:
                    candidates = [root for root in candidates if table[root][0][7] <= root_costs[root]]
                if candidates:
                    break
                if not self.live:
                    table = dynamic_program(self.graph, set(), self.graph.cap, weights)
                    candidates = [root for root in self.remaining if table[root]]
                    if not candidates:
                        raise RuntimeError('no feasible contraction')
                    break
                self.delete(self.victim())

            def priority(root):
                record = table[root][0]
                saved = root_costs[root] - record[7]
                reward = record[7] - record[0]
                if self.ordering == 1:
                    result = (saved + reward, -record[7], -root)
                elif self.ordering == 2:
                    result = (saved / max(1, root_costs[root]), reward / max(1, record[7]), -root)
                elif self.ordering == 3:
                    result = (saved / max(1, root_costs[root]) + reward / max(1, record[7]), record[7], -root)
                else:
                    result = (saved / max(1, root_costs[root]) + reward / max(1, record[7]), -record[7], -root)
                if self.seed:
                    return (result[0] * (0.9 + 0.2 * self.noise[root]), result[1], self.noise[root])
                return result

            root = max(candidates, key=priority)
            if self.release:
                accepted = None
                accepted_score = None
                considered = 0
                for candidate in sorted(candidates, key=priority, reverse=True):
                    trial = None
                    for record in table[candidate][:3]:
                        trial = self.trial(record)
                        if trial is not None:
                            break
                    if trial is None:
                        continue
                    if not self.lookahead:
                        accepted = trial
                        break
                    future_weights = [1.0 / max(1, (mask & trial.remaining_mask).bit_count()) ** self.exponent
                                      for mask in self.user_masks]
                    future = dynamic_program(self.graph, set(trial.live), self.graph.cap, future_weights,
                                             preferred=self.preferred, active=trial.remaining_mask, owned_cached=True)
                    estimate = trial.work + sum(future[root][0][0] if future[root] else root_costs[root]
                                                for root in trial.remaining)
                    score = (estimate, trial.work, trial.peak)
                    if accepted is None or score < accepted_score:
                        accepted = trial
                        accepted_score = score
                    considered += 1
                    if considered >= self.lookahead or deadline is not None and time.monotonic() >= deadline:
                        break
                if accepted is not None:
                    self.__dict__.update(accepted.__dict__)
                    continue
                if self.live:
                    self.delete(self.victim())
                    continue
                raise RuntimeError('no feasible relaxed schedule')
            self.protected = set(self.live)
            self.execute(table[root][0])
            self.protected = set()
            if not self.retain:
                for number in list(self.live):
                    self.delete(number)
        for number in list(self.live):
            self.delete(number)
        return {'steps': self.steps}


def independent(graph):
    table = dynamic_program(graph, set(), graph.cap, [1.0] * len(graph.nodes))
    planner = Planner(graph, retain=False)
    for root in sorted(graph.roots, key=lambda root: -graph.nodes[root].count):
        if root not in planner.remaining:
            continue
        planner.execute(table[root][0])
        for number in list(planner.live):
            planner.delete(number)
    return planner, {'steps': planner.steps}


def compact(case, plan):
    last_use = {}
    sizes = {}
    types = {name: tuple(kinds) for name, kinds in case['tensors'].items()}
    for position, step in enumerate(plan['steps']):
        if 'id' in step:
            name = step['id']
            bindings = {}
            for reference, axes in step['inputs']:
                bindings.update(zip(axes, types[reference]))
                if reference in last_use:
                    last_use[reference] = position
            kinds = tuple(bindings[axis] for axis in step['output'])
            types[name] = kinds
            sizes[name] = math.prod(case['dimensions'][kind] for kind in kinds)
            last_use[name] = position
        elif 'emit' in step:
            name = step['input'][0]
            if name in last_use:
                last_use[name] = position
    release_at = {}
    for name, position in last_use.items():
        release_at.setdefault(position, []).append(name)
    steps = []
    memory = peak = 0
    for position, step in enumerate(plan['steps']):
        if 'delete' in step:
            continue
        steps.append(step)
        if 'id' in step:
            memory += sizes[step['id']]
            peak = max(peak, memory)
        for name in release_at.get(position, ()):
            steps.append({'delete': name})
            memory -= sizes[name]
    return {'steps': steps}, peak


def solve(case):
    started = time.monotonic()
    graph = Graph(case)
    fallback, best = independent(graph)
    best, peak = compact(case, best)
    best_score = (fallback.work, peak)
    deadline = started + 24

    def attempt(**configuration):
        nonlocal best, best_score
        if time.monotonic() >= deadline:
            return
        planner = Planner(graph, **configuration)
        try:
            plan = planner.solve(deadline)
        except (RuntimeError, ValueError):
            return
        if plan is not None:
            plan, peak = compact(case, plan)
            if peak > graph.cap or len(plan['steps']) > 30000:
                return
            score = (planner.work, peak)
            if score < best_score:
                best = plan
                best_score = score

    for exponent, ordering, release in ((0.0, 0, False), (1.0, 0, False),
                                         (0.5, 1, True), (1.0, 0, True)):
        attempt(exponent=exponent, ordering=ordering, release=release)
    lower_bound = 0
    if time.monotonic() < deadline - 3:
        from optimize import optimize, reachable
        choices = optimize(graph, min(deadline - 2, time.monotonic() + 1.0))
        try:
            from global_lp import optimize_lp
            preferred, lower_bound = optimize_lp(graph, choices[0], min(deadline - 1, time.monotonic() + 2.0), with_bound=True)
            choices.insert(0, preferred)
        except (ImportError, ValueError, RuntimeError, MemoryError):
            pass
        seen = set()
        for preferred in choices:
            key = tuple((number, preferred[number]) for number in sorted(reachable(graph, preferred)))
            if key in seen:
                continue
            seen.add(key)
            attempt(preferred=preferred, exponent=0.7, ordering=1, release=True)
            if best_score[0] <= lower_bound * (1 + 1e-10):
                return best
            attempt(preferred=preferred, exponent=0.7, ordering=0)
            if time.monotonic() >= deadline:
                break
    for configuration in (
            {'exponent': 0.5, 'ordering': 1},
            {'exponent': 1.0, 'ordering': 1},
            {'exponent': 0.5, 'ordering': 2},
            {'exponent': 0.0, 'release': True},
            {'exponent': 1.0, 'ordering': 1, 'release': True},
            {'exponent': 1.0, 'release': True, 'lookahead': 2},
            {'exponent': 0.5, 'ordering': 1, 'release': True, 'seed': 211},
            {'exponent': 1.0, 'release': True, 'seed': 11},
            {'exponent': 1.5, 'ordering': 1, 'release': True},
            {'exponent': 0.5, 'ordering': 1, 'release': True, 'frequency_power': 1.0, 'size_power': 1.0},
            {'exponent': 1.0, 'ordering': 3, 'release': True},
            {'exponent': 0.5, 'ordering': 1, 'release': True, 'lookahead': 2},
            {'exponent': 1.0, 'release': True, 'marginal': True}):
        attempt(**configuration)
        if time.monotonic() >= deadline:
            break
    return best


def main():
    with open(sys.argv[1]) as stream:
        case = json.load(stream)
    plan = solve(case)
    with open(sys.argv[2], 'w') as stream:
        json.dump(plan, stream, separators=(',', ':'))


if __name__ == '__main__':
    main()
