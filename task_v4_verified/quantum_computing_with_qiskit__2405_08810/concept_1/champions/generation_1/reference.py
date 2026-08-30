import heapq
import json
import math
import random
import sys


def score(instance, operations):
    edges = {(control, target): (weight, duration) for control, target, weight, duration in instance['edges']}
    ready = [0] * instance['n']
    error = 0
    for kind, control, target in operations:
        if kind == 'cx':
            weight, duration = edges[control, target]
            error += weight
            ready[control] = ready[target] = max(ready[control], ready[target]) + duration
    return error + 0.2 * max(ready)


def simplify(operations):
    output = []
    for operation in operations:
        kind, control, target = operation
        if kind == 'rz':
            output.append(operation)
            continue
        canceled = False
        for position in range(len(output) - 1, -1, -1):
            previous = output[position]
            if previous[0] == 'rz':
                if previous[1] == target:
                    break
            elif previous[1] == control and previous[2] == target:
                del output[position]
                canceled = True
                break
            elif previous[1] == target or previous[2] == control:
                break
        if not canceled:
            output.append(operation)
    return output


class Compiler:
    def __init__(self, instance, variant=0):
        self.instance = instance
        self.size = instance['n']
        self.weights = {(control, target): weight + 0.12 * duration for control, target, weight, duration in instance['edges']}
        self.neighbors = [[] for unused in range(self.size)]
        for control, target in self.weights:
            self.neighbors[control].append(target)
        self.metric = {}
        for control, target in self.weights:
            first = self.weights[control, target]
            second = self.weights[target, control]
            self.metric[control, target] = min(first, second) + (0.2 if variant == 0 else 0.7) * max(first, second)
        self.paths = {}
        self.distances = {}
        for source in range(self.size):
            queue = [(0, source, (source,))]
            visited = set()
            while queue:
                distance, current, path = heapq.heappop(queue)
                if current in visited:
                    continue
                visited.add(current)
                self.paths[source, current] = path
                self.distances[source, current] = distance
                for neighbor in self.neighbors[current]:
                    if neighbor not in visited:
                        heapq.heappush(queue, (distance + self.metric[current, neighbor], neighbor, path + (neighbor,)))
        self.cache = {}

    def plan(self, mask):
        if mask in self.cache:
            return self.cache[mask]
        support = [qubit for qubit in range(self.size) if mask >> qubit & 1]
        if len(support) == 1:
            return 0, [], support[0]
        reached = {support[0]}
        pending = set(support[1:])
        tree_edges = set()
        while pending:
            unused, source, target = min((self.distances[source, target], source, target) for source in reached for target in pending)
            path = self.paths[source, target]
            for control, target in zip(path[:-1], path[1:]):
                tree_edges.add(tuple(sorted((control, target))))
            reached.update(path)
            pending.difference_update(reached)
        parents = list(range(self.size))
        def leader(qubit):
            while parents[qubit] != qubit:
                qubit = parents[qubit]
            return qubit
        tree = [[] for unused in range(self.size)]
        for control, target in sorted(tree_edges, key=lambda edge: self.metric[edge]):
            first, second = leader(control), leader(target)
            if first != second:
                parents[first] = second
                tree[control].append(target)
                tree[target].append(control)
        leaves = [qubit for qubit in reached if len(tree[qubit]) == 1 and not mask >> qubit & 1]
        for qubit in leaves:
            if tree[qubit]:
                neighbor = tree[qubit].pop()
                tree[neighbor].remove(qubit)
                reached.remove(qubit)
                if len(tree[neighbor]) == 1 and not mask >> neighbor & 1:
                    leaves.append(neighbor)
        best = None
        for root in sorted(reached):
            operations = []
            def gather(qubit, parent):
                children = [neighbor for neighbor in tree[qubit] if neighbor != parent]
                if not mask >> qubit & 1:
                    children.sort(key=lambda child: self.weights[qubit, child])
                active = bool(mask >> qubit & 1)
                for child in children:
                    gather(child, qubit)
                    if not active:
                        operations.append((qubit, child))
                        active = True
                    operations.append((child, qubit))
            gather(root, -1)
            cost = sum(self.weights[edge] for edge in operations)
            if best is None or cost < best[0]:
                best = cost, operations, root
        self.cache[mask] = best
        return best

    def compile(self, seed=0, greedy=0):
        randomizer = random.Random(seed)
        pending = dict(enumerate(self.instance['terms']))
        operations = []
        history = []
        potential = [0] + [math.log(count) if greedy == 1 else math.sqrt(count) - 1 for count in range(1, self.size + 2)]
        def apply_gates(gates):
            for control, target in gates:
                operations.append(['cx', control, target])
                history.append(['cx', control, target])
                bit_control = 1 << control
                bit_target = 1 << target
                for index, mask in list(pending.items()):
                    if mask & bit_target:
                        mask ^= bit_control
                        pending[index] = mask
                    if mask & (mask - 1) == 0:
                        operations.append(['rz', mask.bit_length() - 1, index])
                        del pending[index]
        while pending:
            for term, mask in list(pending.items()):
                if mask & (mask - 1) == 0:
                    operations.append(['rz', mask.bit_length() - 1, term])
                    del pending[term]
            if not pending:
                break
            if greedy:
                columns = [0] * self.size
                classes = {}
                for index, mask in pending.items():
                    count = mask.bit_count()
                    classes[count] = classes.get(count, 0) | (1 << index)
                    bits = mask
                    while bits:
                        bit = bits & -bits
                        columns[bit.bit_length() - 1] |= 1 << index
                        bits ^= bit
                best_gain = 0.03
                best_gate = None
                for control, target in self.weights:
                    together = columns[control] & columns[target]
                    apart = columns[target] ^ together
                    gain = sum((together & group).bit_count() * (potential[count] - potential[count - 1]) - (apart & group).bit_count() * (potential[count + 1] - potential[count]) for count, group in classes.items())
                    gain /= self.weights[control, target] ** 0.8
                    if gain > best_gain:
                        best_gain = gain
                        best_gate = control, target
                if best_gate is not None:
                    apply_gates([best_gate])
                    continue
            candidates = []
            for term, mask in pending.items():
                cost, gates, root = self.plan(mask)
                if seed:
                    cost *= randomizer.uniform(0.83, 1.22)
                candidates.append((cost, term, gates, root))
            unused, term, gates, root = min(candidates)
            apply_gates(gates)
        operations.extend(reversed(history))
        return simplify(operations)


def compile_circuit(instance):
    candidates = []
    for variant in range(2):
        compiler = Compiler(instance, variant)
        for seed, greedy in ((0, 0), (17, 0), (91, 0), (0, 1), (17, 1), (0, 2)):
            operations = compiler.compile(seed, greedy)
            candidates.append((score(instance, operations), operations))
    return {'ops': min(candidates, key=lambda item: item[0])[1]}


def main():
    for line in sys.stdin:
        if line.strip():
            print(json.dumps(compile_circuit(json.loads(line)), separators=(',', ':')), flush=True)


if __name__ == '__main__':
    main()
