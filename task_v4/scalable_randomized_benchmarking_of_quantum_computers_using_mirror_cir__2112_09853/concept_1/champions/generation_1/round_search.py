import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
import sys
import itertools
import json
import time
import numpy as np
import networkx as nx
import optimize as opt

SCALE = np.where(opt.ROWS < 24, 2, 1)
LOW = opt.LOWER // SCALE
HIGH = opt.UPPER // SCALE
LABELSET = sorted(set(opt.LABELS.tolist()))


def integer_round(target):
    graph = nx.MultiDiGraph()
    for row in range(32):
        segment = slice(opt.OFFSETS[row], opt.OFFSETS[row + 1])
        supply = (30 if row < 24 else 60) - int(LOW[segment].sum())
        graph.add_node(('row', row), demand=-supply)
    for label in LABELSET:
        demand = int(opt.model.BASELINE_MARGINALS[label] // 2 - LOW[opt.LABELS == label].sum())
        graph.add_node(('label', label), demand=demand)
    for index, (row, label) in enumerate(zip(opt.ROWS, opt.LABELS)):
        for value in range(LOW[index] + 1, HIGH[index] + 1):
            cost = SCALE[index] ** 2 * (2 * value - 1 - 2 * target[index] / SCALE[index])
            graph.add_edge(('row', row), ('label', label), key=value,
                           capacity=1, weight=int(round(cost * 100000)))
    _, flow = nx.network_simplex(graph)
    result = LOW.copy()
    for index, (row, label) in enumerate(zip(opt.ROWS, opt.LABELS)):
        result[index] += sum(flow[('row', row)][('label', label)].values())
    return result * SCALE


def make_moves(even=True):
    moves = []
    for first in range(32):
        for second in range(first + 1, 32):
            shared = set(opt.model.SUPPORTS[first]) & set(opt.model.SUPPORTS[second])
            for label_a, label_b in itertools.combinations(sorted(shared), 2):
                move = np.zeros(len(opt.BASE), dtype=int)
                for row, label, sign in [(first, label_a, 1), (first, label_b, -1),
                                         (second, label_a, -1), (second, label_b, 1)]:
                    index = opt.LOOKUP[(row, label)]
                    multiplier = SCALE[index] if even or second >= 24 else 1
                    move[index] = sign * multiplier
                moves.extend([move, -move])
    return np.array(moves)


MOVES = make_moves(False)
MOVEQ = MOVES @ opt.Q
MOVEQUAD = np.sum(MOVEQ * MOVES, axis=1)
MOVENORM = np.sum(MOVES ** 2, axis=1)
assert np.max(np.abs(opt.A @ MOVES.T)) == 0


def repair(vector, target, rng):
    vector = vector.copy()
    for iteration in range(300):
        difference = int(round(vector @ opt.Q @ vector - 32640))
        if difference == 0:
            return vector
        feasible = np.all((vector + MOVES >= opt.LOWER) & (vector + MOVES <= opt.UPPER), axis=1)
        newdifference = difference + 2 * MOVEQ @ vector + MOVEQUAD
        costs = 2 * MOVES @ (vector - target) + MOVENORM
        exact = np.flatnonzero(feasible & (newdifference == 0))
        if len(exact):
            selected = exact[np.argmin(costs[exact])]
            return vector + MOVES[selected]
        scores = np.abs(newdifference) + .05 * costs
        scores[~feasible] = np.inf
        if iteration % 4 == 3:
            scores += rng.gumbel(size=len(scores)) * 12
        selected = np.argmin(scores)
        vector += MOVES[selected]
    return None


if __name__ == '__main__':
    source = sys.argv[1] if len(sys.argv) > 1 else 'continuous_0.npy'
    repeats = int(sys.argv[2]) if len(sys.argv) > 2 else 100
    target = np.load(source)
    print('TARGET', opt.fit(opt.curve(target)), 'q', target @ opt.Q @ target, flush=True)
    print('MOVES', len(MOVES), flush=True)
    rng = np.random.default_rng(20260828)
    best = 0
    for trial in range(repeats):
        perturbed = target + rng.normal(size=len(target)) * (0 if trial == 0 else .25 + trial % 8 * .2)
        rounded = integer_round(perturbed)
        vector = repair(rounded, target, rng)
        if vector is None:
            print('REPAIR FAILED', trial, flush=True)
            continue
        witness = opt.artifact(vector)
        opt.model.check_constraints(witness)
        metrics = opt.fit(opt.curve(vector))
        if metrics['relative_bias'] > best:
            best = metrics['relative_bias']
            print('BEST', trial, metrics, 'distance', np.linalg.norm(vector - target), flush=True)
            with open('integer_best.json', 'w') as handle:
                json.dump(witness, handle, indent=2)
            if best >= .0244 and metrics['max_residual'] <= .004:
                with open('witness.json', 'w') as handle:
                    json.dump(witness, handle, indent=2)
                print('PASSED', opt.model.evaluate(witness), flush=True)
