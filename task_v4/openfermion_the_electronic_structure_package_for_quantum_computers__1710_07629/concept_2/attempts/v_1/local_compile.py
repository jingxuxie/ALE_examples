import argparse
import itertools
import time
from functools import lru_cache

from peel import *


class LocalCompiler:
    def __init__(self, instance, seed=0):
        self.instance = instance
        self.size = instance['n_modes']
        self.initial = np.array([int(mode in instance['initial_occupied']) for mode in range(self.size)])
        self.neighbors = [set() for mode in range(self.size)]
        for first, second in instance['edges']:
            self.neighbors[first].add(second)
            self.neighbors[second].add(first)
        self.random = np.random.default_rng(seed)
        self.random_trees = False

    @lru_cache(None)
    def subsets(self, active, size):
        active_set = set(active)
        groups = {frozenset([mode]) for mode in active}
        for length in range(1, size):
            expanded = set()
            for group in groups:
                boundary = set.union(*(self.neighbors[mode] for mode in group)) & active_set
                for mode in boundary - group:
                    expanded.add(group | {mode})
            groups = expanded
        return np.array(sorted(tuple(sorted(group)) for group in groups), dtype=int)

    def freeze(self, matrix, active):
        return tuple(mode for mode in active if abs(matrix[mode, mode].real - self.initial[mode]) > 1e-11)

    def split_valid(self, matrix, active):
        remaining = set(active)
        while remaining:
            component = {remaining.pop()}
            frontier = list(component)
            for mode in frontier:
                added = self.neighbors[mode] & remaining
                remaining.difference_update(added)
                component.update(added)
                frontier.extend(added)
            if remaining and np.linalg.norm(matrix[np.ix_(list(component), list(remaining))]) > 1e-8:
                return False
        return True

    def options(self, matrix, active, extra=0):
        first_size = None
        for size in range(2, len(active) + 1):
            if first_size is not None and size > first_size + extra:
                break
            subsets = self.subsets(active, size)
            if not len(subsets):
                continue
            blocks = matrix[subsets[:, :, None], subsets[:, None, :]]
            values, vectors = np.linalg.eigh(blocks)
            for group_index, eigen_index in zip(*np.where((abs(values) < 1e-12) | (abs(values - 1) < 1e-12))):
                subset = subsets[group_index]
                occupation = int(values[group_index, eigen_index] > 0.5)
                vector = vectors[group_index, :, eigen_index]
                for root in subset:
                    if self.initial[root] != occupation:
                        continue
                    for variant in range(1):
                        result, gates = self.eliminate(matrix, subset, vector, root, variant)
                        after = self.freeze(result, active)
                        if not self.split_valid(result, after):
                            continue
                        first_size = size if first_size is None else first_size
                        yield result, gates, after, root

    def eliminate(self, matrix, subset, vector, root, variant=0):
        support = set(subset)
        parent = {root: None}
        order = [root]
        for mode in order:
            neighbors = sorted(self.neighbors[mode] & support)
            if variant or self.random_trees:
                self.random.shuffle(neighbors)
            for neighbor in neighbors:
                if neighbor not in parent:
                    parent[neighbor] = mode
                    order.append(neighbor)
        orbital = np.zeros(self.size, dtype=complex)
        orbital[subset] = vector
        result = matrix.copy()
        gates = []
        for child in reversed(order[1:]):
            ancestor = parent[child]
            upper, lower = orbital[ancestor], orbital[child]
            if abs(lower) < 1e-12:
                continue
            theta = math.atan2(abs(lower), abs(upper))
            phi = float(np.angle(-lower / upper)) if abs(upper) > 1e-15 else 0.0
            gate = ancestor, child, theta, phi
            result = rotate(result, *gate)
            orbital[ancestor] = math.cos(theta) * upper - np.exp(-1j * phi) * math.sin(theta) * lower
            orbital[child] = 0.0
            gates.append(gate)
        return result, gates

    def run(self, trials=10, prefix=None, suffix='local'):
        best = (100000, 100000)
        best_resource = -1.0
        for trial in range(trials):
            matrix = target(self.instance)
            for gate in prefix or []:
                matrix = rotate(matrix, *gate)
            active = self.freeze(matrix, tuple(range(self.size)))
            all_gates = list(prefix or [])
            while active:
                choices = []
                for result, gates, after, root in self.options(matrix, active):
                    depth = len(schedule(all_gates + gates, self.size))
                    impurity = np.sum(result.diagonal().real * (1 - result.diagonal().real))
                    degree = len(self.neighbors[root] & set(active))
                    count = len(gates) / (len(active) - len(after))
                    if trial == 0:
                        rank = (count, degree, impurity, depth)
                    elif trial == 1:
                        rank = (count, depth, impurity, degree)
                    else:
                        rank = (count + self.random.exponential(0.6), degree + self.random.normal(), impurity)
                    choices.append((rank, result, gates, after))
                if not choices:
                    break
                _, matrix, gates, active = min(choices, key=lambda item: item[0])
                all_gates.extend(gates)
            error = np.linalg.norm(matrix - np.diag(self.initial))
            inverse = [(first, second, -theta, phi) for first, second, theta, phi in reversed(all_gates)]
            layers = schedule(inverse, self.size)
            score = (len(all_gates), len(layers))
            print(self.instance['id'], trial, score, error, 'cache', self.subsets.cache_info().currsize, flush=True)
            resource = min(1.0, self.instance['budgets']['max_gates'] / max(1, score[0]), self.instance['budgets']['max_depth'] / max(1, score[1]))
            if error < 1e-8 and (resource > best_resource or (resource == best_resource and score < best)):
                best = score
                best_resource = resource
                Path(self.instance['id'] + '_' + suffix + '.json').write_text(json.dumps({'id': self.instance['id'], 'layers': layers}))
                if resource == 1:
                    print('SOLVED', self.instance['id'], flush=True)
                    return


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--index', type=int, default=0)
    parser.add_argument('--trials', type=int, default=10)
    parser.add_argument('--hybrid', action='store_true')
    parser.add_argument('--random-trees', action='store_true')
    arguments = parser.parse_args()
    instance = INSTANCES[arguments.index]
    prefix = []
    if arguments.hybrid:
        circuit = json.loads(Path(instance['id'] + '_rank.json').read_text())
        prefix = [(gate['u'], gate['v'], -gate['theta'], gate['phi']) for layer in reversed(circuit['layers']) for gate in layer]
    compiler = LocalCompiler(instance)
    compiler.random_trees = arguments.random_trees
    compiler.run(arguments.trials, prefix, 'tree' if arguments.random_trees else ('hybrid' if arguments.hybrid else 'local'))
