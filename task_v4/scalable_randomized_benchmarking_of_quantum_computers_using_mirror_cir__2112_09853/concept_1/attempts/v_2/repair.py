import itertools
import json
import sys
import time

from search import *
from scipy.optimize import linprog

SCALE = np.array([2.] * 72 + [1.] * 120)
UNWEIGHTED = np.vstack([ROW_MATRIX, MARGINAL_MATRIX / model.WEIGHTS[LAYERS]])
UNWEIGHTED = UNWEIGHTED[pivots[:RANK]]
CYCLES = []
for first, second in itertools.combinations(range(32), 2):
    shared = sorted(set(model.SUPPORTS[first]) & set(model.SUPPORTS[second]))
    for one, two in itertools.combinations(shared, 2):
        CYCLES.append([LOOKUP[first, one], LOOKUP[first, two], LOOKUP[second, one], LOOKUP[second, two]])
LIB.repair.argtypes = [INTEGER, DOUBLE, INTEGER, INTEGER, INTEGER, INTEGER,
                       ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_double, INTEGER]
LIB.repair.restype = ctypes.c_int


def rounded(target, seed):
    target = target / SCALE
    rng = np.random.default_rng(seed)
    lower = np.floor(target + 1e-7)
    upper = np.ceil(target - 1e-7)
    costs = 1 - 2 * (target - lower) + rng.normal(0, .1, 192)
    result = linprog(costs, A_eq=UNWEIGHTED, b_eq=np.zeros(RANK),
                     bounds=list(zip(lower, upper)), method='highs')
    if not result.success:
        raise ValueError(result.message)
    return np.ascontiguousarray(np.rint(result.x * SCALE), dtype=np.int32)


def make_cycles(lower, upper, seed=0):
    available = upper > lower
    cycles = [[first + 1, -second - 1, -third - 1, fourth + 1]
              for first, second, third, fourth in CYCLES
              if np.all(available[[first, second, third, fourth]])]
    global_index = {pauli: index + 32 for index, pauli in enumerate(np.unique(PAULIS))}
    endpoints = [(int(layer), global_index[pauli]) for layer, pauli in zip(LAYERS, PAULIS)]
    rng = np.random.default_rng(seed)
    for trial in range(20):
        adjacency = [[] for index in range(80)]
        for edge in rng.permutation(np.flatnonzero(available)):
            source, destination = endpoints[edge]
            parents = {source: None}
            queue = [source]
            for node in queue:
                if destination in parents:
                    break
                for neighbor, previous_edge in adjacency[node]:
                    if neighbor not in parents:
                        parents[neighbor] = (node, previous_edge)
                        queue.append(neighbor)
            if destination not in parents:
                adjacency[source].append((destination, edge))
                adjacency[destination].append((source, edge))
            else:
                path = [int(edge) + 1]
                node = destination
                sign = -1
                while node != source:
                    node, previous_edge = parents[node]
                    path.append(sign * (int(previous_edge) + 1))
                    sign = -sign
                cycles.append(path)
    unique = {}
    for cycle in cycles:
        canonical = tuple(sorted(cycle))
        opposite = tuple(sorted(-entry for entry in cycle))
        unique[min(canonical, opposite)] = cycle
    cycles = list(unique.values())
    width = max(map(len, cycles)) + 1
    encoded = np.zeros((len(cycles), width), dtype=np.int32)
    for index, cycle in enumerate(cycles):
        encoded[index, 0] = len(cycle)
        encoded[index, 1:len(cycle)+1] = cycle
    return encoded


def main():
    source = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    target = np.load(ROOT / f'continuous_{source}.npy')
    objective = Objective()
    objective.calculate(target)
    frozen = (target < LOWER + 1e-4) | (target > UPPER - 1e-4)
    if len(sys.argv) > 2:
        frozen[:72] = False
    lower = LOWER.astype(np.int32)
    upper = UPPER.astype(np.int32)
    lower[frozen] = np.rint(target[frozen]).astype(np.int32)
    upper[frozen] = lower[frozen]
    cycles = make_cycles(lower, upper)
    print('target', source, objective.metrics, 'cycles', len(cycles), 'frozen', frozen.sum(), flush=True)
    best_bias = 0
    for trial in range(200):
        counts = rounded(target, trial)
        statistics = np.zeros(3, dtype=np.int32)
        result = LIB.repair(counts, target, lower, upper,
                            PARTNER.astype(np.int32), cycles, len(cycles), cycles.shape[1], 3000000,
                            trial + 1234, 0.2, statistics)
        if result:
            witness = artifact(counts)
            model.check_constraints(witness)
            objective.calculate(counts)
            metrics = objective.metrics.copy()
            if metrics['bias'] > best_bias:
                best_bias = metrics['bias']
                (ROOT / f'best_{source}.json').write_text(json.dumps(witness))
            print('feasible', trial, metrics, 'statistics', statistics, flush=True)
            if metrics['bias'] >= .0239 and metrics['residual'] <= .004 and metrics['tail'] >= .005:
                (ROOT / 'witness.json').write_text(json.dumps(witness, indent=2) + '\n')
                print('SUCCESS', model.evaluate(witness), flush=True)
                return
        else:
            print('failed', trial, statistics, flush=True)


if __name__ == '__main__':
    main()
