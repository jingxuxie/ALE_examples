import argparse
import json
from pathlib import Path

import numpy as np
from scipy.special import expit

from landscape import best_sector
from search import optimize
from verify import BOUND, EDGES, evaluate


ROOT = Path(__file__).resolve().parent


def construct(base, free, seed):
    core = [site for site in range(16) if site not in free]
    core_count = len(core)
    count = 1 << core_count
    states = np.ones((count, 16))
    states[:, core] = 1 - 2 * ((np.arange(count)[:, None] >> np.arange(core_count)) & 1)
    energy = np.zeros(count)
    free_couplings = np.zeros((len(free), 16))
    for edge, (first, second) in enumerate(EDGES):
        coupling = base['bonds'][edge]
        if first in free:
            free_couplings[free.index(first), second] = coupling
        elif second in free:
            free_couplings[free.index(second), first] = coupling
        else:
            energy -= coupling * states[:, first] * states[:, second]
    fields = states @ free_couplings.T
    free_logits = fields * BOUND / 4
    aligned = np.tanh(free_logits / 2)
    costs = energy - energy[0] + ((free_logits / 2 - fields) * aligned - np.log(np.cosh(free_logits / 2))).sum(axis=1)
    variances = ((free_logits / 2 - fields) ** 2 * (1 - aligned ** 2)).sum(axis=1)
    edge_logits = np.where((costs > 3.5) & (costs < BOUND), costs, BOUND - 1e-10)
    penalties = expit(-edge_logits) * ((costs - edge_logits) ** 2 + variances)
    rng = np.random.default_rng(seed)
    if seed:
        penalties *= np.exp(rng.normal(0, .3, count))
    penalties += rng.uniform(0, 1e-9, count)
    forests = np.full(count, np.inf)
    trees = np.full(count, np.inf)
    forest_choices = np.zeros(count, dtype=int)
    roots = np.zeros(count, dtype=int)
    forests[0] = 0
    for mask in sorted(range(1, count), key=int.bit_count):
        members = [index for index in range(core_count) if mask & (1 << index)]
        root = min(members, key=lambda index: forests[mask ^ (1 << index)])
        trees[mask] = penalties[mask] + forests[mask ^ (1 << root)]
        roots[mask] = root
        first_bit = mask & -mask
        subset = mask
        best_value, best_subset = np.inf, 0
        while subset:
            if subset & first_bit:
                value = trees[subset] + forests[mask ^ subset]
                if value < best_value:
                    best_value, best_subset = value, subset
            subset = (subset - 1) & mask
        forests[mask] = best_value
        forest_choices[mask] = best_subset
    full = count - 1
    root = int(roots[full])
    parents = {root: None}
    subtrees = {}

    def walk(mask, parent):
        while mask:
            subtree = int(forest_choices[mask])
            child = int(roots[subtree])
            parents[child] = parent
            subtrees[child] = subtree
            walk(subtree ^ (1 << child), child)
            mask ^= subtree

    walk(full ^ (1 << root), root)
    order_indices = [root]
    for parent in order_indices:
        order_indices.extend(child for child in parents if parents[child] == parent)
    order = [core[index] for index in order_indices] + free
    inverse = np.argsort(order)
    weights = np.zeros((16, 16))
    for child, parent in parents.items():
        if parent is not None:
            weights[inverse[core[child]], inverse[core[parent]]] = edge_logits[subtrees[child]]
    for free_index, site in enumerate(free):
        weights[inverse[site], :core_count] = free_couplings[free_index, order[:core_count]] * (BOUND - 1e-10) / 4
    witness = json.loads(json.dumps(base))
    witness['weights'] = weights.tolist()
    witness['order'] = order
    print('DP', seed, 'proxy', forests[full ^ (1 << root)], 'order', order,
          'costs', [round(costs[subtrees[child]], 6) for child in order_indices[1:]], flush=True)
    return witness


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, default=ROOT / 'three_30_minimax.json')
    parser.add_argument('--count', type=int, default=6)
    parser.add_argument('--iterations', type=int, default=250)
    parser.add_argument('--tag', default='three30')
    parser.add_argument('--free', type=int, nargs='+', default=[4, 6, 13])
    arguments = parser.parse_args()
    base = json.loads(arguments.input.read_text())
    for seed in range(arguments.count):
        witness = construct(base, arguments.free, seed)
        witness, sector = best_sector(witness)
        filename = ROOT / f'general_{arguments.tag}_{seed}_initial.json'
        filename.write_text(json.dumps(witness, indent=2) + '\n')
        print('initial', seed, evaluate(witness)['metrics'], flush=True)
        witness, result = optimize(witness, objective='variance', constraints=False,
                                   iterations=arguments.iterations, verbosity=0)
        witness, sector = best_sector(witness)
        report = evaluate(witness)
        filename = ROOT / f'general_{arguments.tag}_{seed}.json'
        filename.write_text(json.dumps(witness, indent=2) + '\n')
        print('variance', seed, report['core_score'], report['metrics'], flush=True)
        witness, result = optimize(witness, objective='minimax', constraints=False,
                                   iterations=350, verbosity=0)
        witness, sector = best_sector(witness)
        report = evaluate(witness)
        filename = ROOT / f'general_{arguments.tag}_{seed}_minimax.json'
        filename.write_text(json.dumps(witness, indent=2) + '\n')
        print('minimax', seed, report['core_score'], report['metrics'], flush=True)


if __name__ == '__main__':
    main()
