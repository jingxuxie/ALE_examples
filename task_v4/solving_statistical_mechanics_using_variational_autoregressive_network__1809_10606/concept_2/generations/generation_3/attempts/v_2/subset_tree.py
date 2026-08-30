import argparse
import json
from pathlib import Path

import numpy as np

from landscape import best_sector
from search import Problem, optimize
from verify import BOUND, EDGES, LOWER, evaluate


ROOT = Path(__file__).resolve().parent
FREE = [4, 6, 13, 15]
CORE = [site for site in range(16) if site not in FREE]


def prepare(base):
    configurations = np.ones((4096, 16))
    configurations[:, CORE] = 1 - 2 * ((np.arange(4096)[:, None] >> np.arange(12)) & 1)
    core_energy = np.zeros(4096)
    free_couplings = np.zeros((4, 16))
    for edge, (first, second) in enumerate(EDGES):
        coupling = base['bonds'][edge]
        if first in FREE:
            free_couplings[FREE.index(first), second] = coupling
        elif second in FREE:
            free_couplings[FREE.index(second), first] = coupling
        else:
            core_energy -= coupling * configurations[:, first] * configurations[:, second]
    fields = configurations @ free_couplings.T
    costs = core_energy - core_energy[0] - np.log(np.cosh(fields)).sum(axis=1)
    return costs, free_couplings


def dynamic_tree(base, costs, free_couplings, seed, node_penalties=None):
    rng = np.random.default_rng(seed)
    logits = np.where((costs > 3.5) & (costs < BOUND), costs, BOUND - 1e-10)
    penalties = .01 * (costs - logits) ** 2
    if node_penalties is not None:
        penalties = node_penalties.copy()
    if seed:
        penalties *= np.exp(rng.normal(0, .3, 4096))
    penalties += rng.uniform(0, 1e-9, 4096)
    forests = np.full(4096, np.inf)
    trees = np.full(4096, np.inf)
    forest_choices = np.zeros(4096, dtype=int)
    root_choices = np.zeros(4096, dtype=int)
    forests[0] = 0
    masks = sorted(range(1, 4096), key=int.bit_count)
    for mask in masks:
        members = [index for index in range(12) if mask & (1 << index)]
        root = min(members, key=lambda index: forests[mask ^ (1 << index)])
        trees[mask] = penalties[mask] + forests[mask ^ (1 << root)]
        root_choices[mask] = root
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
    full = 4095
    root = int(root_choices[full])
    parents = {root: None}
    subtree_masks = {}

    def walk_forest(mask, parent):
        while mask:
            subtree = int(forest_choices[mask])
            child = int(root_choices[subtree])
            parents[child] = parent
            subtree_masks[child] = subtree
            walk_forest(subtree ^ (1 << child), child)
            mask ^= subtree

    walk_forest(full ^ (1 << root), root)
    order_indices = [root]
    for parent in order_indices:
        order_indices.extend(child for child in parents if parents[child] == parent)
    order = [CORE[index] for index in order_indices] + FREE
    inverse = np.argsort(order)
    weights = np.zeros((16, 16))
    for child, parent in parents.items():
        if parent is not None:
            weights[inverse[CORE[child]], inverse[CORE[parent]]] = logits[subtree_masks[child]]
    for free_index, site in enumerate(FREE):
        weights[inverse[site], :12] = free_couplings[free_index, order[:12]] * (BOUND - 1e-10) / 4
    witness = json.loads(json.dumps(base))
    witness['weights'] = weights.tolist()
    witness['order'] = order
    print('DP', seed, 'proxy', forests[full ^ (1 << root)], 'order', order,
          'cuts', [round(costs[subtree_masks[child]], 6) for child in order_indices[1:]], flush=True)
    return witness


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, default=ROOT / 'beta1_free_sector.json')
    parser.add_argument('--count', type=int, default=10)
    parser.add_argument('--iterations', type=int, default=240)
    arguments = parser.parse_args()
    base = json.loads(arguments.input.read_text())
    costs, free_couplings = prepare(base)
    for seed in range(arguments.count):
        witness = dynamic_tree(base, costs, free_couplings, seed)
        witness, sector = best_sector(witness)
        print('initial', seed, evaluate(witness)['metrics'], flush=True)
        witness, result = optimize(witness, objective='variance', constraints=False,
                                   iterations=arguments.iterations, verbosity=0)
        witness, sector = best_sector(witness)
        report = evaluate(witness)
        filename = ROOT / f'subset_{seed}.json'
        filename.write_text(json.dumps(witness, indent=2) + '\n')
        print('variance', seed, report['core_score'], report['metrics'], flush=True)
        if report['metrics']['reward_variance'] < .25:
            witness, result = optimize(witness, objective='minimax', constraints=False,
                                       iterations=300, verbosity=0)
            witness, sector = best_sector(witness)
            report = evaluate(witness)
            filename = ROOT / f'subset_{seed}_minimax.json'
            filename.write_text(json.dumps(witness, indent=2) + '\n')
            print('minimax', seed, report['core_score'], report['metrics'], flush=True)


if __name__ == '__main__':
    main()
